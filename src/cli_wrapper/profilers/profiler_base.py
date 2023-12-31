from abc import ABC, abstractmethod
from typing import Optional
import logging
import sys
import os
import argparse
from multiprocessing import Process

logging.basicConfig()
logger = logging.getLogger()


class CLISubCommand:
    """
    Mixin: interface to processes designed to be run by a CLI wrapper.
    """

    @classmethod
    def configure_cli(cls, parser: argparse.ArgumentParser) -> None:
        """
        Configure a CLI parser or subparser with profiler options.

        The default implementation is a no-op (i.e., it doesn't add or alter
        any CLI arguments or options).

        Args:
            parser: argparse.ArgumentParser object to configure
        """
        pass

    @abstractmethod
    def run(self, opts: argparse.Namespace) -> None:
        """
        Run the process with CLI arguments parsed by the owning/master process.
        """
        ...


class CLIWrapper:
    """
    Mixin: interface for a CLI script with multiple subcommands.

    Also supports multiple groups of related subcommands.
    """

    def __init__(
        self,
        prog: Optional[str] = None,
        description: Optional[str] = None,
        epilog: Optional[str] = None,
    ) -> None:
        """
        Args:
            prog: Name of script or program to display in helptext.  Defaults
                to self.__class__.__name__.
            description: Short description of this CLIWrapper.
            epilog: Text to be displayed **after** the autogenerated helptext
                for all commands, subcommands, and options associated with
                this CLIWrapper.
        """
        prog = prog if prog is not None else self.__class__.__name__
        self._parser = argparse.ArgumentParser(
            prog=prog, description=description, epilog=epilog
        )
        self._subcommand_groups = {}

    def add_subcommand_group(
        self,
        group_name: str,
        description: Optional[str] = None,
        required: Optional[bool] = False,
        helptext: Optional[str] = None,
    ) -> argparse._SubParsersAction:
        """
        Add a subcommand group with the specified name.

        Args:
            group_name: Name of subcommand group
            description: Brief description of subcommand group
            required: True if the user must specify a value of this subcommand
            helptext: Top-level helptext to display for this group

        Returns:
            An instance of argparse._SubParsersAction associated with the new
                subcommand group
        """
        self._subcommand_groups[group_name] = self._parser.add_subparsers(
            title=group_name,
            description=description,
            required=required,
            help=helptext,
        )
        return self._subcommand_groups[group_name]

    def add_subcommand(
        self, group_name: str, subcmd: CLISubCommand, helptext: Optional[str] = None
    ) -> None:
        """
        Add an instance of CLISubCommand to a subcommand group of self.

        Since all additional parser configuration is handled by the
        CLISubCommand instance added as a subcommand, the bare subparser
        object is not returned.

        Args:
            group_name: Name of subcommand group to which subcmd should be
                added.  If a group with this name does not already exist, it
                will be created and added to self._subcommand_groups.
            subcmd: Instance of CLISubCommand to add as a subcommand.
            helptext: Top-level helptext for this particular subcommand.
        """
        try:
            name = subcmd.name
        except AttributeError:
            name = subcmd.__class__.__name__
        subparser = self._subcommand_groups.setdefault(
            group_name, self.add_subcommand_group(group_name)
        ).add_parser(name, help=helptext)
        subparser.set_defaults(**{group_name: subcmd.run})
        subcmd.configure_cli(subparser)

    def add_argument(self, *args, **kwargs):
        """
        A passthrough to argparse.ArgumentParser.add_argument.
        """
        self._parser.add_argument(*args, **kwargs)

    def run(self):
        args = self._parser.parse_args(sys.argv[1:])


class Profiler(ABC, CLISubCommand):
    @staticmethod
    def _get_script_globals(script_filename):
        return {
            "__file__": script_filename,
            "__name__": "__main__",
            "__package__": None,
            "__cached__": None,
        }

    def profile_script(self, script_file, outfile=None):
        with open(script_file, "rb") as main:
            code = compile(main.read(), script_file, "exec")
        self.profile_code(
            code, globals=self._get_script_globals(script_file), outfile=outfile
        )

    @abstractmethod
    def profile_code(self, raw_code, gloals={}, locals={}, outfile=None):
        ...


class CProfile(Profiler):
    import cProfile

    def profile_code(self, raw_code, globals={}, locals={}, outfile=None):
        self.cProfile.runctx(raw_code, globals, None, outfile, -1)


class Scalene(Profiler):
    from scalene.scalene_profiler import Scalene

    def profile_code(self, raw_code, globals={}, locals={}, outfile=None):
        self.Scalene.profile_code(self, raw_code, globals, locals)

    def configure_cli(cls, parser: ArgumentParser) -> None:
        parser.addArgument(
            "--html",
            help="Output Scalene profiling results in HTML form",
            action="store_true",
        )


class PyInstrument(Profiler):
    from pyinstrument import profiler

    def profile_code(self, raw_code, globals={}, locals={}, outfile=None):
        pass
