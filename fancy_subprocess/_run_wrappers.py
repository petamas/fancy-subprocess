__all__ = [
    'run_silenced',
    'run_indented',
]

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Optional

from typing_extensions import Unpack

from fancy_subprocess._run_core import run, RunResult
from fancy_subprocess._run_param import change_default_run_params, check_run_params, RunParams
from fancy_subprocess._utils import oslex_join

def run_silenced(
    cmd: Sequence[str | Path],
    *,
    print_message: Optional[Callable[[str], None]] = None,
    **kwargs: Unpack[RunParams],
) -> RunResult:
    """
    Specialized version of `fancy_subprocess.run()`, primarily used to run a command and later process its output.

    Differences from `fancy_subprocess.run()`:
    - `print_output` is not customizable, it is always set to `fancy_subprocess.SILENCE`, which disables printing the command's output.
    - `description` is customizable, but its default value (used when it is either not specified or set to `None`) changes to `Running command (output silenced): ...`.

    All other `fancy_subprocess.run()` arguments are available and behave the same.
    """

    check_run_params(**kwargs)

    forwarded_args = kwargs.copy()
    change_default_run_params(forwarded_args, description=f'Running command (output silenced): {oslex_join(cmd)}')

    return run(
        cmd,
        print_message=print_message,
        print_output=lambda line: None,
        **forwarded_args,
    )

def run_indented(
    cmd: Sequence[str | Path],
    *,
    print_message: Optional[Callable[[str], None]] = None,
    indent: str | int = 4,
    **kwargs: Unpack[RunParams],
) -> RunResult:
    """
    Specialized version of `fancy_subprocess.run()` which prints the command's output indented by a user-defined amount.

    The `print_output` argument is replaced by `indent`, which can be set to either the number of spaces to use for indentation or any custom indentation string (eg. `\t`).

    All other `fancy_subprocess.run()` arguments are available and behave the same.
    """

    check_run_params(**kwargs)

    if isinstance(indent, int):
        indent = indent*' '

    return run(
        cmd,
        print_message=print_message,
        print_output=lambda line: print(f'{indent}{line}', flush=True),
        **kwargs,
    )
