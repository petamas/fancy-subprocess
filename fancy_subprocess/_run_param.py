__all__ = [
    'ANY_EXIT_CODE',
    'AnyExitCode',
]

class AnyExitCode:
    """
    Use an instance of this class (eg. fancy_subprocess.ANY_EXIT_CODE) as the 'success' argument to make run() and related functions treat any exit code as success.
    """

    pass

ANY_EXIT_CODE = AnyExitCode()
