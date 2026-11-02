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
    parser.add_argument(
        "-b",
        "--no-banner",
        action="store_true",
        help="Suppress the startup banner",
    )

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
    common.add_argument(
        "-r", "--runners-dir",
        metavar="DIR",
        help="Where GE-Proton is discovered/stored (independent from install_dir and prefix)",
    )
    common.add_argument(
        "-p", "--proton-prefix",
        metavar="DIR",
        help="Steam Proton prefix to use (typically a compatdata/<appid>/pfx folder; default: Steam-managed runtime path)",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser(
        "setup",
        parents=[common],
        help="Setup the environment for the modpack installation",
        description="Download archives and create the install directories and base folder structure.",
    )

    sub.add_parser(
        "install",
        parents=[common],
        help="Download and install the modpack",
        description="Verify and install the ZONA modpack.",
    )

    sub.add_parser(
        "delete",
        parents=[common],
        help="Remove the installed files and directories",
        description="Remove the installed ZONA files and directories.",
    )

    mo2_parser = argparse.ArgumentParser(add_help=False)
    mo2_parser.add_argument(
        "-i", "--install-dir",
        metavar="DIR",
        help="Where to install ZONA (default: install_dir from config.toml)",
    )
    mo2_parser.add_argument(
        "-r", "--runners-dir",
        metavar="DIR",
        help="Where GE-Proton is discovered/stored (independent from install_dir and prefix)",
    )
    mo2_parser.add_argument(
        "-p", "--proton-prefix",
        metavar="DIR",
        help="Steam Proton prefix to use (typically a compatdata/<appid>/pfx folder; default: Steam-managed runtime path)",
    )

    sub.add_parser(
        "mo2",
        parents=[mo2_parser],
        help="Install or validate just Mod Organizer 2 in the Proton prefix",
        description="Ensure the MO2 installation exists without re-running the full modpack install flow.",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        raise SystemExit
    return args