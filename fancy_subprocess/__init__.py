import os
import shutil
import sys
import time
from contextlib import AbstractContextManager
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Optional

import oslex
import subprocess
if sys.platform=='win32':
    from ntstatus import NtStatus, NtStatusSeverity, ThirtyTwoBits
else:
    import signal

def which(name: str, *, path: Optional[str | Sequence[str | Path]] = None, cwd: Optional[str | Path] = None) -> Optional[Path]:
    """
    Wrapper for `shutil.which()` which returns the result as an absolute `Path` (or `None` if it fails to find the executable). It also has a couple extra features, see below.

    Arguments (all of them except `name` are optional):
    - `name: str` - Executable name to look up.
    - `path: None | str | Sequence[str | Path]` - Directory list to look up `name` in. If set to `None`, or set to a string, then it is passed to `shutil.which()` as-is. If set to a list, concatenates the list items using `os.pathsep`, and passes the result to `shutil.which()`. Defaults to `None`. See `shutil.which()`'s documentation on exact behaviour of this argument.
    - `cwd: Optional[str | Path]` - If specified, then changes the current working directory to `cwd` for the duration of the `shutil.which()` call. Note that since it is changing global state (the current working directory), it is inherently not thread-safe.
    """

    if path is not None and not isinstance(path, str):
        path = os.pathsep.join(str(d) for d in path)

    old_cwd = Path.cwd()
    if cwd is not None:
        os.chdir(cwd)

    try:
        result = shutil.which(name, path=path)
    finally:
        if cwd is not None:
            os.chdir(old_cwd)

    if result is not None:
        return Path(result).absolute()
    else:
        return None

def checked_which(name: str, *, path: Optional[str | Sequence[str | Path]] = None, cwd: Optional[str | Path] = None) -> Path:
    """
    Same as `fancy_subprocess.which()`, except it raises `ValueError` instead of returning `None` if it cannot find the executable.
    """

    result = which(name, path=path, cwd=cwd)
    if result is not None:
        return result
    else:
        raise ValueError(f'Could not find executable in PATH: "{name}"')

def _oslex_join(cmd: Sequence[str | Path]) -> str:
    return oslex.join([str(arg) for arg in cmd])

def _stringify_exit_code(exit_code: int) -> Optional[str]:
    if sys.platform=='win32':
        # Windows
        try:
            bits = ThirtyTwoBits(exit_code)
        except ValueError:
            return None

        try:
            code = NtStatus(bits)
            if code.severity!=NtStatusSeverity.STATUS_SEVERITY_SUCCESS:
                return code.name
        except ValueError:
            pass

        return f'0x{bits.unsigned_value:08X}'
    else:
        # POSIX
        if exit_code<0:
            try:
                return signal.Signals(-exit_code).name
            except ValueError:
                return 'unknown signal'

    return None

class AnyExitCode:
    """
    Use an instance of this class (eg. fancy_subprocess.ANY_EXIT_CODE) as the 'success' argument to make run() and related functions treat any exit code as success.
    """

    pass

ANY_EXIT_CODE = AnyExitCode()

@dataclass(kw_only=True, frozen=True)
class RunProcessResult:
    """
    `fancy_subprocess.run()` and similar functions return a `RunProcessResult` instance on success.

    `RunProcessResult` has the following properties:
    - `exit_code: int` - Exit code of the finished process. (On Windows, this is a signed `int32` value, i.e. in the range of \[-2<sup>31</sup>, 2<sup>31</sup>-1\].)
    - `output: str` - Combination of the process's output on stdout and stderr.
    """

    exit_code: int
    output: str

@dataclass(kw_only=True, frozen=True)
class RunProcessError(Exception):
    """
    `fancy_subprocess.run()` and similar functions raise `RunProcessError` on error. There are two kinds of errors that result in a `RunProcessError`:
    - If the requested command has failed, the `completed` property will be `True`, and the `exit_code` and `output` properties will be set.
    - If the command couldn't be run (eg. because the executable wasn't found), the `completed` property will be `False`, and the `oserror` property will be set to the `OSError` exception instance originally raised by the underlying `subprocess.Popen()` call.

    Calling `str()` on a `RunProcessError` object returns a detailed one-line description of the error:
    - The failed command is included in the message.
    - If an `OSError` happened, its message is included in the message.
    - On Windows, if the exit code of the process is recognized as a known `NTSTATUS` error value, its name is included in the message, otherwise its hexadecimal representation is included (to make searching it on the internet easier).
    - On Unix systems, if the exit code represents a signal, its name is included in the message.

    `RunProcessError` has the following properties:
    - `cmd: Sequence[str | Path]` - Original command passed to `fancy_subprocess.run()`.
    - `completed: bool` - `True` if the process completed (with an error), `False` if the underlying `subprocess.Popen()` call raised an OSError (eg. because it could not start the process).
    - `exit_code: int` - Exit code of the completed process. Raises `ValueError` if `completed` is `False`.
    - `output: str` - Combination of the process's output on stdout and stderr. Raises `ValueError` if `completed` is `False`.
    - `oserror: OSError` - The `OSError` raised by `subprocess.Popen()`. Raises `ValueError` if `completed` is `True`.
    """

    cmd: Sequence[str | Path]
    result: RunProcessResult | OSError

    @property
    def completed(self) -> bool:
        return isinstance(self.result, RunProcessResult)

    @property
    def exit_code(self) -> int:
        if isinstance(self.result, RunProcessResult):
            return self.result.exit_code
        else:
            raise ValueError('...')

    @property
    def output(self) -> str:
        if isinstance(self.result, RunProcessResult):
            return self.result.output
        else:
            raise ValueError('...')

    @property
    def oserror(self) -> OSError:
        if isinstance(self.result, OSError):
            return self.result
        else:
            raise ValueError('...')

    def __str__(self) -> str:
        if isinstance(self.result, RunProcessResult):
            exit_code_str = _stringify_exit_code(self.exit_code)
            if exit_code_str is not None:
                exit_code_comment = f' ({exit_code_str})'
            else:
                exit_code_comment = ''
            return f'Command failed with exit code {self.exit_code}{exit_code_comment}: {_oslex_join(self.cmd)}'
        else:
            return f'Exception {type(self.result).__name__} with message "{str(self.result)}" was raised while trying to run command: {_oslex_join(self.cmd)}'

def SILENCE(msg: str) -> None:
    """
    Helper function that takes a string, and does nothing with it. Meant to be passed as the print_message or print_output argument of run() and related functions to silence the corresponding output stream.
    """

    pass

def run(
    cmd: Sequence[str | Path],
    *,
    print_message: Optional[Callable[[str], None]] = None,
    print_output: Optional[Callable[[str], None]] = None,
    description: Optional[str] = None,
    success: Sequence[int] | AnyExitCode | None = None,
    flush_before_subprocess: bool = True,
    max_output_size: int = 10*1000*1000,
    retry: int = 0,
    retry_initial_sleep_seconds: float = 10,
    retry_backoff: float = 2,
    env_overrides: Optional[Mapping[str, str]] = None,
    cwd: Optional[str | Path] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> RunProcessResult:
    """
    An extended (and in some aspects, constrained) version of `subprocess.run()`. It runs a command and prints its output line-by-line using a customizable `print_output` function, while printing informational messages (eg. which command it is running) using a customizable `print_message` function.

    Key differences compared to `subprocess.run()`:
    - The command must be specified as a list, simply specifying a string is not allowed.
    - The command's stdout and stderr is always combined into a single stream. (Like `subprocess.run(stderr=STDOUT)`.)
    - The output of the command is always assumed to be textual, not binary. (Like `subprocess.run(text=True)`.)
    - The output of the command is always captured, but it is also immediately printed using `print_output`.
    - The exit code of the command is checked, and an exception is raised on failure, like `subprocess.run(check=True)`, but the list of exit codes treated as success is customizable, and the raised exception is `RunProcessError` instead of `CalledProcessError`.
    - `OSError` is never raised, it gets converted to `RunProcessError`.
    - `RunProcessResult` is returned instead of `CompletedProcess` on success.

    Arguments (all of them except `cmd` are optional):
    - `cmd: Sequence[str | Path]` - Command to run. See `subprocess.run()`'s documentation for the interpretation of `cmd[0]`. It is recommended to use `fancy_subprocess.which()` to produce `cmd[0]`.
    - `print_message: Optional[Callable[[str], None]]` - Function used to print informational messages. If not set or `None`, defaults to `print(flush=True)`. Use `print_message=fancy_subprocess.SILENCE` to disable printing informational messages.
    - `print_output: Optional[Callable[[str], None]]` - Function used to print a line of the output of the command. If not set or `None`, defaults to `print(flush=True)`. Use `print_message=fancy_subprocess.SILENCE` to disable printing the command's output.
    - `description: Optional[str]` - Description printed before running the command. If not set or `None`, defaults to `Running command: ...`.
    - `success: Sequence[int] | AnyExitCode | None` - List of exit codes that should be considered successful. If set to `fancy_subprocess.ANY_EXIT_CODE`, then all exit codes are considered successful. If not set or `None`, defaults to `[0]`. Note that 0 is not automatically included in the list of successful exit codes, so if a list without 0 is specified, then the function will consider 0 a failure.
    - `flush_before_subprocess: bool` - If `True`, flushes both the standard output and error streams before running the command. Defaults to `True`.
    - `max_output_size: int` - Maximum number of characters to be recorded in the `output` field of `RunProcessResult`. If the command produces more than `max_output_size` characters, only the last `max_output_size` will be recorded. Defaults to 10,000,000.
    - `retry: int` - Number of times to retry running the command on failure. Note that the total number of attempts is one greater than what's specified. (I.e. `retry=2` attempts to run the command 3 times.) Defaults to 0.
    - `retry_initial_sleep_seconds: float` - Number of seconds to wait before retrying for the first time. Defaults to 10.
    - `retry_backoff: float` - Factor used to increase wait times before subsequent retries. Defaults to 2.
    - `env_overrides: Optional[Mapping[str, str]]` - Dictionary used to set environment variables. Note that unline the `env` argument of `subprocess.run()`, `env_overrides` does not need to contain all environment variables, only the ones you want to add/modify compared to os.environ.
    - `cwd: Optional[str | Path]` - If not `None`, change current working directory to `cwd` before running the command.
    - `encoding: Optional[str]` - This encoding will be used to open stdout and stderr of the command. If not set or `None`, see default behaviour in `io.TextIOWrapper`'s documentation.
    - `errors: Optional[str]` - This specifies how text decoding errors will be handled. See details in `io.TextIOWrapper`'s documentation.
    """

    if print_message is None:
        print_message = lambda msg: print(msg, flush=True)

    if print_output is None:
        print_output = lambda line: print(line, flush=True)

    if description is None:
        description = f'Running command: {_oslex_join(cmd)}'

    if success is None:
        success = [0]

    env = dict(os.environ)
    if env_overrides is not None:
        if sys.platform=='win32':
            env.update((key.upper(), value) for key,value in env_overrides.items())
        else:
            env.update(env_overrides)

    def run_with_params() -> RunProcessResult:
        return _run_internal(
                cmd,
                print_message=print_message,
                print_output=print_output,
                description=description,
                success=success,
                flush_before_subprocess=flush_before_subprocess,
                max_output_size=max_output_size,
                env=env,
                cwd=cwd,
                encoding=encoding,
                errors=errors)

    sleep_seconds = retry_initial_sleep_seconds
    for attempts_left in range(retry, 0, -1):
        try:
            return run_with_params()
        except RunProcessError as e:
            print_message(str(e))
            if attempts_left!=1:
                plural = 's'
            else:
                plural = ''
            print_message(f'Retrying in {sleep_seconds} seconds ({attempts_left} attempt{plural} left)...')
            time.sleep(sleep_seconds)
            sleep_seconds *= retry_backoff

    return run_with_params()

def _run_internal(
    cmd: Sequence[str | Path],
    *,
    print_message: Callable[[str], None],
    print_output: Callable[[str], None],
    description: str,
    success: Sequence[int] | AnyExitCode,
    flush_before_subprocess: bool,
    max_output_size: int,
    env: dict[str, str],
    cwd: Optional[str | Path],
    encoding: Optional[str],
    errors: Optional[str],
) -> RunProcessResult:
    print_message(description)

    if flush_before_subprocess:
        sys.stdout.flush()
        sys.stderr.flush()

    output = ''
    try:
        with subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=cwd, env=env, encoding=encoding, errors=errors) as proc:
            assert proc.stdout is not None # passing stdout=subprocess.PIPE guarantees this

            for line in iter(proc.stdout.readline, ''):
                line = line.removesuffix('\n')
                print_output(line)

                output += line + '\n'
                if len(output)>max_output_size+1:
                    output = output[-max_output_size-1:] # drop the beginning of the string

            proc.wait()
            result = RunProcessResult(exit_code=proc.returncode, output=output.removesuffix('\n'))
    except OSError as e:
        raise RunProcessError(cmd=cmd, result=e) from e

    if isinstance(success, AnyExitCode) or result.exit_code in success:
        return result
    else:
        raise RunProcessError(cmd=cmd, result=result)

def run_indented(
    cmd: Sequence[str | Path],
    *,
    print_message: Optional[Callable[[str], None]] = None,
    indent: str | int = 4,
    description: Optional[str] = None,
    success: Sequence[int] | AnyExitCode | None = None,
    flush_before_subprocess: bool = True,
    max_output_size: int = 10*1000*1000*1000,
    retry: int = 0,
    retry_initial_sleep_seconds: float = 10,
    retry_backoff: float = 2,
    env_overrides: Optional[Mapping[str, str]] = None,
    cwd: Optional[str | Path] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> RunProcessResult:
    """
    Specialized version of `fancy_subprocess.run()` which prints the command's output indented by a user-defined amount.

    The `print_output` argument is replaced by `indent`, which can be set to either the number of spaces to use for indentation or any custom indentation string (eg. `\t`).

    All other `fancy_subprocess.run()` arguments are available and behave the same.
    """

    if isinstance(indent, int):
        indent = indent*' '

    return run(
        cmd,
        print_message=print_message,
        print_output=lambda line: print(f'{indent}{line}', flush=True),
        description=description,
        success=success,
        flush_before_subprocess=flush_before_subprocess,
        max_output_size=max_output_size,
        retry=retry,
        retry_initial_sleep_seconds=retry_initial_sleep_seconds,
        retry_backoff=retry_backoff,
        env_overrides=env_overrides,
        cwd=cwd,
        encoding=encoding,
        errors=errors,
    )

def run_silenced(
    cmd: Sequence[str | Path],
    *,
    print_message: Optional[Callable[[str], None]] = None,
    description: Optional[str] = None,
    success: Sequence[int] | AnyExitCode | None = None,
    flush_before_subprocess: bool = True,
    max_output_size: int = 10*1000*1000*1000,
    retry: int = 0,
    retry_initial_sleep_seconds: float = 10,
    retry_backoff: float = 2,
    env_overrides: Optional[Mapping[str, str]] = None,
    cwd: Optional[str | Path] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> RunProcessResult:
    """
    Specialized version of `fancy_subprocess.run()`, primarily used to run a command and later process its output.

    Differences from `fancy_subprocess.run()`:
    - `print_output` is not customizable, it is always set to `fancy_subprocess.SILENCE`, which disables printing the command's output.
    - `description` is customizable, but its default value (used when it is either not specified or set to `None`) changes to `Running command (output silenced): ...`.

    All other `fancy_subprocess.run()` arguments are available and behave the same.
    """

    if description is None:
        description = f'Running command (output silenced): {_oslex_join(cmd)}'

    return run(
        cmd,
        print_message=print_message,
        print_output=SILENCE,
        description=description,
        success=success,
        flush_before_subprocess=flush_before_subprocess,
        max_output_size=max_output_size,
        retry=retry,
        retry_initial_sleep_seconds=retry_initial_sleep_seconds,
        retry_backoff=retry_backoff,
        env_overrides=env_overrides,
        cwd=cwd,
        encoding=encoding,
        errors=errors,
    )
