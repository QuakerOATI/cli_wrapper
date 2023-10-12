#!/bin/env python

"""CLI wrapper for Project_Driver_Load.py.

The main purpose of this script is to import some constants and load the
configuration file, updating keys with values from a local configuration file
and environment variables as described in the configuration module, before
running the project driver code itself.

In addition, the CLI exposes options to run the driver script under cProfile,
or alternatively under any specified wrapper command that can be run from the
shell.
"""

import logging
import site
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import List
from Utilities.configuration import build_config_file, PROJECT_ROOT
from Utilities.code_runners import (
    cprofile,
    wrap_with_shell_command,
    run_script,
    make_script_globals,
)


def _with_default(msg: str, format_spec: str = "s") -> str:
    """Specify a predefined default value in a help message.

    Args:
        msg: help message to format
        format_spec (optional): printf-style format specifier; defaults to "s"

    Returns:
        Input help message with "(default: %(default){format_spec})" appended
    """
    return f"{msg} (default: %(default){format_spec})"


def parse_cli_args(args: List[str]):
    """Parse command-line options and parameters.

    Args:
        args: command-line to parse (usually sys.argv[1:])

    Returns:
        :obj:`argparse.Namespace`: CLI parameters namespace
    """

    # use module docstring as helptext header
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--outfile", help="Write results to file", default=None)
    parser.add_argument(
        "-a",
        "--logappend",
        help="Append to output file rather than overwrite it",
        action="store_const",
        dest="logmode",
        const="a",
        default="w",
    )
    parser.add_argument(
        "--withprofiler",
        help=_with_default(
            """
Run the specified entry point under a profiling tool.  Any argument other than 'cprofile' will be parsed and run as a shell command.
        """
        ),
        default=None,
        dest="profiler",
    )
    parser.add_argument(
        "--entrypoint",
        help=_with_default("Python entry point to run"),
        default=PROJECT_ROOT.joinpath("LoadForecast", "Project_Driver_Load.py"),
        type=Path,
    )
    parser.add_argument(
        "-c",
        "--configfile",
        help=_with_default(
            """
Write data from file to global project configuration file before running.  May be specified multiple times.
        """
        ),
        type=Path,
        action="append",
        default=PROJECT_ROOT.joinpath("configuration.local.yaml"),
        dest="configfiles",
        metavar="configfile.{json,yml,yaml}",
    )
    parser.add_argument(
        "-C",
        "--base-config",
        help=_with_default(
            """
Base configuration filepath .  Any additional configuration files specified using -c or --configfile will be merged into the configuration object read from this file.
        """
        ),
        default=PROJECT_ROOT.joinpath("configuration.base.json"),
        type=Path,
        dest="base_config",
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Print debug output",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose output",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
        default=logging.WARNING,
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_cli_args(sys.argv[1:])

    # TODO: Refactor into logging module
    logging.basicConfig(level=args.loglevel)
    logger = logging.getLogger(__name__)
    logger.debug("Parsed CLI options: %s", args)

    logger.debug("Building config file...")
    build_config_file(args.base_config, *args.configfiles)

    logger.debug("Adding to sitedir: %s, %s", PROJECT_ROOT, args.script.parent)
    site.addsitedir(PROJECT_ROOT)
    site.addsitedir(args.script.parent)

    G = make_script_globals(args.script)
    logger.debug("Using globals %r for script execution", G)

    if args.profiler is None:
        logger.info("Running driver script %s without profiling", args.script)
        run_script(args.script, G, args.outfile, True)
    elif args.profiler.lower() == "cprofile":
        logger.info(
            "Running driver script %s with cProfile enabled (output file: %s)",
            args.script,
            args.outfile,
        )
        cprofile(args.script, args.outfile)
    else:
        # Anything other than cProfile will be interpreted as a shell command
        # TODO: Finish implementing Scalene and PyInstrument modules
        logger.info(
            "Running command %s with script %s as argument", args.profiler, args.script
        )
        wrap_with_shell_command(args.profiler, args.script, args.outfile)
