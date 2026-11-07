import argparse
import tomllib
from pathlib import Path


def read_toml_configs():
    with open(Path(__file__).parent.parent / "config.toml", "rb") as f:
        return tomllib.load(f)


def resolve_alternatives(artifacts, archives_dir):
    """Point artifacts with `alternatives` at whichever copy is on disk.

    The primary filename/md5 wins if present; otherwise the first alternative found in
    archives_dir replaces it. Mutates the artifact dicts in place so every later step
    (verification, extraction) sees the same file. Returns the list for convenience.
    """
    for artifact in artifacts:
        alternatives = artifact.get("alternatives")
        if not alternatives or (Path(archives_dir) / artifact["filename"]).is_file():
            continue
        found = next((alt for alt in alternatives if (Path(archives_dir) / alt["filename"]).is_file()), None)
        if found is not None:
            artifact["primary"] = {"filename": artifact["filename"], "md5": artifact["md5"]}
            artifact["filename"] = found["filename"]
            artifact["md5"] = found["md5"]
    return artifacts


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

    download_parser = argparse.ArgumentParser(add_help=False)
    download_parser.add_argument(
        "-a", "--archives-dir",
        metavar="DIR",
        help="Where downloaded archives are stored (default: archives_dir from config.toml)",
    )

    sub.add_parser(
        "download",
        parents=[download_parser],
        help="Download and verify the archive set without setting up the prefix",
        description="Fetch the ZONA archives and validate their checksums without creating the Proton prefix or installing the modpack.",
    )

    sub.add_parser(
        "setup",
        parents=[common],
        help="Setup the environment for the modpack installation",
        description="Download archives and create the install directories and base folder structure.",
    )

    install_parser = sub.add_parser(
        "install",
        parents=[common],
        help="Download and install the modpack",
        description="Verify and install the ZONA modpack.",
    )
    install_parser.add_argument(
        "--steam",
        action="store_true",
        help="Also add Mod Organizer 2 to the Steam library"
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

    sub.add_parser(
        "steam",
        parents=[mo2_parser],
        help="Add Mod Organizer 2 to the Steam library as a non-Steam game",
        description="Add ZONA's Mod Organizer 2 to the Steam library, forced to GE-Proton and using the installed prefix. Steam must be closed.",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        raise SystemExit
    return args