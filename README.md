# fancy-subprocess

`fancy-subprocess` provides variants of `subprocess.run()` with formatted output, detailed error messages and retry capabilities.

## `fancy_subprocess.run()` and related functionality

An extended (and in some aspects, constrained) version of `subprocess.run()`. It runs a command and prints its output line-by-line using a customizable `print_output` function, while printing informational messages (eg. which command it is running) using a customizable `print_message` function.

Key differences compared to `subprocess.run()`:
- The command must be specified as a list, simply specifying a string is not allowed.
- The command's stdout and stderr is always combined into a single stream. (Like `subprocess.run(stderr=STDOUT)`.)
- The output of the command is always assumed to be textual, not binary. (Like `subprocess.run(text=True)`.)
- The output of the command is always captured, but it is also immediately printed using `print_output`.
- The exit code of the command is checked, and an exception is raised on failure, like `subprocess.run(check=True)`, but the list of exit codes treated as success is customizable, and the raised exception is `RunError` instead of `CalledProcessError`.
- `OSError` is never raised, it gets converted to `RunError`.
- `RunResult` is returned instead of `CompletedProcess` on success.

Arguments (all of them except `cmd` are optional):
- `cmd: Sequence[str | Path]` - Command to run. See `subprocess.run()`'s documentation for the interpretation of `cmd[0]`. It is recommended to use `fancy_subprocess.which()` to produce `cmd[0]`.
- `print_message: Callable[[str], None]` - Function used to print informational messages. If unspecified or set to `None`, defaults to `fancy_subprocess.default_print`. Use `message_quiet=True` to disable printing informational messages.
	- The type of this argument is also aliased as `fancy_subprocess.PrintFunction`.
- `print_output: Callable[[str], None]` - Function used to print a line of the output of the command. If unspecified or set to `None`, defaults to `fancy_subprocess.default_print`. Use `output_quiet=True` to disable printing the command's output.
	- The type of this argument is also aliased as `fancy_subprocess.PrintFunction`.
- `message_quiet: bool` - If `True`, `print_message` is ignored, and no informational messages are printed. If unspecified or set to `None`, defaults to `False`.
- `output_quiet: bool` - If `True`, `print_output` is ignored, and the command's output it not printed. If unspecified or set to `None`, defaults to `False`. Note that this parameter also affects the default value of `description`.
- `description: str` - Description printed before running the command. If unspecified or set to `None`, defaults to `Running command: ...` when `output_quiet` is `False`, and `Running command (output silenced): ...` when `output_quiet` is `True`.
- `success: Sequence[int] | AnyExitCode` - List of exit codes that should be considered successful. If set to `fancy_subprocess.ANY_EXIT_CODE`, then all exit codes are considered successful. If unspecified or set to `None`, defaults to `[0]`. Note that 0 is not automatically included in the list of successful exit codes, so if a list without 0 is specified, then the function will consider 0 a failure.
	- The type of this argument is also aliased as `fancy_subprocess.Success`.
- `flush_before_subprocess: bool` - If `True`, flushes both the standard output and error streams before running the command. If unspecified or set to `None`, defaults to `True`.
- `max_output_size: int` - Maximum number of characters to be recorded in the `output` field of `RunResult`. If the command produces more than `max_output_size` characters, only the last `max_output_size` will be recorded. If unspecified or set to `None`, defaults to 10,000,000.
- `retry: int` - Number of times to retry running the command on failure. Note that the total number of attempts is one greater than what's specified. (I.e. `retry=2` attempts to run the command 3 times.) If unspecified or set to `None`, defaults to 0.
- `retry_initial_sleep_seconds: float` - Number of seconds to wait before retrying for the first time. If unspecified or set to `None`, defaults to 10.
- `retry_backoff: float` - Factor used to increase wait times before subsequent retries. If unspecified or set to `None`, defaults to 2.
- `env_overrides: Mapping[str, str]` - Dictionary used to set environment variables. Note that unline the `env` argument of `subprocess.run()`, `env_overrides` does not need to contain all environment variables, only the ones you want to add/modify compared to os.environ. If unspecified or set to `None`, defaults to empty dictionary, i.e. no change to the environment.
	- The type of this argument is also aliased as `fancy_subprocess.EnvOverrides`.
- `cwd: str | Path` - If not `None`, change current working directory to `cwd` before running the command.
- `encoding: str` - This encoding will be used to open stdout and stderr of the command. If unspecified or set to `None`, see default behaviour in `io.TextIOWrapper`'s documentation.
- `errors: str` - This specifies how text decoding errors will be handled. See details (including what happens if unspecified or set to `None`) in `io.TextIOWrapper`'s documentation.

### Return value: `fancy_subprocess.RunResult`

`fancy_subprocess.run()` and similar functions return a `RunResult` instance on success.

`RunResult` has the following properties:
- `exit_code: int` - Exit code of the finished process. (On Windows, this is a signed `int32` value, i.e. in the range of \[-2<sup>31</sup>, 2<sup>31</sup>-1\].)
- `output: str` - Combination of the process's output on stdout and stderr.

### Exception: `fancy_subprocess.RunError`

`fancy_subprocess.run()` and similar functions raise `RunError` on error. There are two kinds of errors that result in a `RunError`:
- If the requested command has failed, the `completed` property will be `True`, and the `exit_code` and `output` properties will be set.
- If the command couldn't be run (eg. because the executable wasn't found), the `completed` property will be `False`, and the `oserror` property will be set to the `OSError` exception instance originally raised by the underlying `subprocess.Popen()` call.

Calling `str()` on a `RunError` object returns a detailed one-line description of the error:
- The failed command is included in the message.
- If an `OSError` happened, its message is included in the message.
- On Windows, if the exit code of the process is recognized as a known `NTSTATUS` error value, its name is included in the message, otherwise its hexadecimal representation is included (to make searching it on the internet easier).
- On Unix systems, if the exit code represents a signal, its name is included in the message.

`RunError` has the following properties:
- `cmd: Sequence[str | Path]` - Original command passed to `fancy_subprocess.run()`.
- `completed: bool` - `True` if the process completed (with an error), `False` if the underlying `subprocess.Popen()` call raised an OSError (eg. because it could not start the process).
- `exit_code: int` - Exit code of the completed process. Raises `ValueError` if `completed` is `False`.
- `output: str` - Combination of the process's output on stdout and stderr. Raises `ValueError` if `completed` is `False`.
- `oserror: OSError` - The `OSError` raised by `subprocess.Popen()`. Raises `ValueError` if `completed` is `True`.

### `fancy_subprocess.run_silenced()`

Specialized version of `fancy_subprocess.run()`, primarily used to run a command and later process its output.

Differences compared to `fancy_subprocess.run()`:
- `output_quiet` cannot be set from the calling side, it is always set to `True`. Note that this affects `description`'s default value.
- `print_output` cannot be set from the calling side (because it wouldn't matter anyway because of `output_quiet=True`).

All other `fancy_subprocess.run()` arguments are available and behave the same.

### `fancy_subprocess.run_indented()`

Specialized version of `fancy_subprocess.run()` which prints the command's output indented by a user-defined amount.

The `print_output` argument is replaced by `indent`, which can be set to either the number of spaces to use for indentation or any custom indentation string (eg. `\t`).

All other `fancy_subprocess.run()` arguments are available and behave the same.

### Example outputs

#### Success

Take this script:

```
import fancy_subprocess
import sys

fancy_subprocess.run_indented(
    [sys.executable, '-m', 'venv', '--help'],
    print_message=lambda msg: print(f'[script-name] {msg}'),
    success=fancy_subprocess.ANY_EXIT_CODE)
```

Running the script will produce the following output (on Windows):

```
[script-name] Running command: d:\projects\python-libs\fancy_subprocess\.venv\Scripts\python.exe -m venv --help
    usage: venv [-h] [--system-site-packages] [--symlinks | --copies] [--clear]
                [--upgrade] [--without-pip] [--prompt PROMPT] [--upgrade-deps]
                ENV_DIR [ENV_DIR ...]

    Creates virtual Python environments in one or more target directories.

    positional arguments:
      ENV_DIR               A directory to create the environment in.

    options:
      -h, --help            show this help message and exit
      --system-site-packages
                            Give the virtual environment access to the system
                            site-packages dir.
      --symlinks            Try to use symlinks rather than copies, when symlinks
                            are not the default for the platform.
      --copies              Try to use copies rather than symlinks, even when
                            symlinks are the default for the platform.
      --clear               Delete the contents of the environment directory if it
                            already exists, before environment creation.
      --upgrade             Upgrade the environment directory to use this version
                            of Python, assuming Python has been upgraded in-place.
      --without-pip         Skips installing or upgrading pip in the virtual
                            environment (pip is bootstrapped by default)
      --prompt PROMPT       Provides an alternative prompt prefix for this
                            environment.
      --upgrade-deps        Upgrade core dependencies: pip setuptools to the
                            latest version in PyPI

    Once an environment has been created, you may wish to activate it, e.g. by
    sourcing an activate script in its bin directory.
```


#### Failed command on Windows

Take this script:

```
import fancy_subprocess
import sys

try:
    fancy_subprocess.run(
        [sys.executable, '-c', 'import sys; print("Noooooo!"); sys.exit(-1072103376)'],
        description='Demonstrating failure...',
    )
except fancy_subprocess.RunError as e:
    print(e)
```

Running the script on Windows will produce the following output (-1072103376 is the signed integer interpretation of 0xC0190030, i.e. `STATUS_LOG_CORRUPTION_DETECTED`):

```
Demonstrating failure...
Noooooo!
Command failed with exit code -1072103376 (STATUS_LOG_CORRUPTION_DETECTED): d:\projects\python-libs\fancy_subprocess\.venv\Scripts\python.exe -c "import sys; print("\^"Noooooo^!\^""); sys.exit(-1072103376)"
```

#### Killed command on Linux

Take this script:

```
import fancy_subprocess
import sys

try:
    fancy_subprocess.run_silenced(
        [sys.executable, '-c', 'import time; time.sleep(60)'],
        description='Sweet dreams!',
    )
except fancy_subprocess.RunError as e:
    print(e)
```

Running the script on Linux and killing the subprocess using `kill -9` before the 60 seconds are up will result in the following output:

```
Sweet dreams!
Command failed with exit code -9 (SIGKILL): /home/petamas/.venv/bin/python -c 'import time; time.sleep(60)'
 ```

#### Failure to find executable

Take this script:

```
import fancy_subprocess

try:
    fancy_subprocess.run(['foo', '--bar', 'baz'])
except fancy_subprocess.RunError as e:
    print(e)
```

Running the script will produce the following output (exact error message may depend on OS):

```
Running command: foo --bar baz
Exception FileNotFoundError with message "[Errno 2] No such file or directory: 'foo'" was raised while trying to run command: foo --bar baz
```

## Other utilities

### `fancy_subprocess.which()`

Wrapper for `shutil.which()` which returns the result as an absolute `Path` (or `None` if it fails to find the executable). It also has a couple extra features, see below.

Arguments (all of them except `name` are optional):
- `name: str` - Executable name to look up.
- `path: None | str | Sequence[str | Path]` - Directory list to look up `name` in. If set to `None`, or set to a string, then it is passed to `shutil.which()` as-is. If set to a list, concatenates the list items using `os.pathsep`, and passes the result to `shutil.which()`. Defaults to `None`. See `shutil.which()`'s documentation on exact behaviour of this argument.
- `cwd: Optional[str | Path]` - If specified, then changes the current working directory to `cwd` for the duration of the `shutil.which()` call. Note that since it is changing global state (the current working directory), it is inherently not thread-safe.

### `fancy_subprocess.checked_which()`

Same as `fancy_subprocess.which()`, except it raises `ValueError` instead of returning `None` if it cannot find the executable.

## Licensing

This library is licensed under the MIT license.
