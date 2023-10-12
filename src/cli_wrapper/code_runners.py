"""Utilities for running Python code, files, and modules from a script.
"""

from pathlib import Path
from typing import Dict, Any, Optional


def make_script_globals(script: Path, name="__main__", **kwargs) -> Dict[str, Any]:
    """Get the standard Python globals associated with a standalone script.

    Args:
        script: :obj:`pathlib.Path`: of script
        name: Value of __name__ to include in the results (defaults to
            "__main__")
        **kwargs: Additional key-value pairs to include in results

    Returns:
        :obj:`dict`: of globals suitable for consumption by cProfile,
            :obj:`runpy.run_module`, and similar
    """
    G = {
        "__file__": str(script.resolve()),
        "__name__": name,
        "__package__": None,
        "__cached__": None,
    }
    G.update(kwargs)
    return G


def cprofile(script: Path, globals: Dict[str, Any], outfile: Optional[Path]) -> None:
    """Run the specified Python file under cProfile.

    Args:
        script: :obj:`pathlib.Path`: of entry point to run
        globals: dict containing global variable names and values to export to
            the script (see :func:`make_script_globals`:)
        outfile: :obj:`pathlib.Path`: to which stdout and stderr of the
            spawned process should be redirected
    """
    import cProfile

    with script.open("rb") as driver:
        code = compile(driver.read(), str(script), "exec")
    cProfile.runctx(code, globals, None, outfile, -1)


def wrap_with_shell_command(
    cmd: str, script: Path, outfile: Optional[Path], write_mode: str = "w"
) -> None:
    """Run the shell command 'cmd "script"' in a child process.

    Should correctly handle keyboard interrupts by forwarding a SIGINT to the
    child process.

    Args:
        cmd: Shell command to run
        script: :obj:`pathlib.Path`: of entry point to pass as an argument to
            cmd
        outfile: :obj:`pathlib.Path`: to which stdout and stderr of the
            spawned process should be redirected
        write_mode: Mode with which to open the file descriptor for outfile.
            Valid options are "w" (which will overwrite the file if it
            already exists) and "a" (which will append to the file if it
            already exists and create it if not).
    """
    import shlex
    import subprocess
    import signal

    shell_cmd = [shlex.quote(word) for word in shlex.split(cmd)]
    shell_cmd.append(shlex.quote(str(script)))

    if outfile is not None:
        with outfile.open(write_mode) as ostream:
            process = subprocess.Popen(
                shell_cmd, stdout=ostream, stderr=ostream, universal_newlines=True
            )
    else:
        process = subprocess.Popen(
            shell_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    while True:
        # The outer loop guards against multiple keyboard interrupts
        # TODO: Add option to:
        #   * periodically poll for status
        #   * write benchmarking data to stdout during run
        try:
            process.wait()
            exit(0)
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)


def run_script(
    script: Path,
    globals: Dict[str, Any],
    outfile: Optional[Path],
    write_mode: str = "w",
    as_module: bool = True,
) -> None:
    """Execute a standalone Python script.

    Args:
        script: :obj:`pathlib.Path` of the script to be run
        globals: dict containing global variable names and values to export to
            the script (see :func:`make_script_globals`:)
        outfile: :obj:`pathlib.Path`: to which stdout and stderr of the
            spawned process should be redirected
        write_mode: Mode with which to open the file descriptor for outfile.
            Valid options are "w" (which will overwrite the file if it
            already exists) and "a" (which will append to the file if it
            already exists and create it if not).
        as_module: whether to run the script by importing it as a module, as
            opposed to as a standalone executable (defaults to True)
    """
    import runpy
    from contextlib import redirect_stdout, redirect_stderr

    runner = runpy.run_module if as_module else runpy.run_path

    if outfile is not None:
        with outfile.open(write_mode) as outstream:
            with redirect_stderr(outstream), redirect_stdout(outstream):
                runner(script.stem, init_globals=globals, run_name="__main__")
    else:
        runner(str(script.resolve()), init_globals=globals, run_name="__main__")
