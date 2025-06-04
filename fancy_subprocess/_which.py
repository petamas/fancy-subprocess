__all__ = [
    'which',
    'checked_which',
]

import shutil
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

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
