__all__ = [
    'RunProcessError',
    'RunProcessResult',
    'SILENCE',
]

from fancy_subprocess._run_core import RunError, RunResult

RunProcessError = RunError
RunProcessResult = RunResult

def SILENCE(msg: str) -> None:
    """
    Helper function that takes a string, and does nothing with it. Meant to be passed as the print_message or print_output argument of run() and related functions to silence the corresponding output stream.
    """

    pass
