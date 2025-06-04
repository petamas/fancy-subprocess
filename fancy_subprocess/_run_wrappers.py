__all__ = [
    'run_silenced',
    'run_indented',
]

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Optional

from fancy_subprocess._run_core import run, RunProcessResult
from fancy_subprocess._run_param import AnyExitCode
from fancy_subprocess._utils import oslex_join

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
        description = f'Running command (output silenced): {oslex_join(cmd)}'

    return run(
        cmd,
        print_message=print_message,
        print_output=lambda line: None,
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
