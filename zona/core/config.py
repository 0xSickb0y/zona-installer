import argparse
import tomllib
from pathlib import Path


def read_toml_configs():
    with open(Path(__file__).parent.parent / "config.toml", "rb") as f:
        return tomllib.load(f)


def get_project_version():
    return read_toml_configs()["project"]["version"] 


def cli_arguments():
    parser = argparse.ArgumentParser(prog="zona")
    parser.add_argument("--version", action="version", version=get_project_version())
    common = argparse.ArgumentParser(add_help=False)

    common.add_argument(
        "-i", "--install-dir",
        metavar="DIR",
        help="Where to install ZONA (default: install_dir from config.toml)",
    )
    
    common.add_argument(
        "-a", "--archives-dir",
        metavar="DIR",
        help="Where downloaded archives are stored (default: archives_dir from config.toml)",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    
    sub.add_parser(
        "setup",
        parents=[common],
        help="Setup the environment for the modpack installation",
        description="Download archives and create the install directories and base folder structure.",
    )
    
    sub.add_parser( # TODO: add flags like --steam / --lutris here later
        "install",
        parents=[common],
        help="Download and install the modpack",
        description="Verify and install the ZONA modpack."
    )
    
    sub.add_parser(
        "delete",
        parents=[common],
        help="Remove the installed files and directories",
        description="Remove the installed ZONA files and directories.",
    )

    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        raise SystemExit
    return args