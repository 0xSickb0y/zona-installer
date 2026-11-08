import os
import sys
import shutil
from zona import mo2
from zona import setup
from zona import install
from zona import download
from zona.install import steam
from zona.setup import path_ops
from zona.core import config, utils
from zona.core.log import logger, setup_logging


WINE_COMMANDS = {"setup", "install", "mo2"}  # commands that run Proton's Wine


def main():
    setup_logging()
    args = config.cli_arguments()
    if args.command in WINE_COMMANDS:
        restart_in_fhs()
    version = config.get_project_version()
    paths = path_ops.resolve_paths(
        config.read_toml_configs(),
        getattr(args, "install_dir", None),
        getattr(args, "archives_dir", None),
        getattr(args, "runners_dir", None),
        getattr(args, "proton_prefix", None),
        getattr(args, "runner", None),
    )

    print(f"S.T.A.L.K.E.R.: Anomaly - ZONA modpack v{version} installer for Linux.")

    if not args.no_banner:
        yellow = "\033[33m"
        reset = "\033[0m"
        banner = f"""
{yellow}
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣠⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡖⠁⠀⠀⠀⠀⠀⠀⠈⢲⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀    ⠀⠀⠀⠀⠀⠀⠀⣠⡴⠞⠛⠉⠉⠉⠀⠈⠉⠉⠙⠛⠷⢦⣀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣼⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣧⠀⠀⠀⠀⠀⠀⠀⠀    ⠀⠀⠀⠀⢀⣴⠟⢁⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣄⡉⠳⣄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣸⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⣇⠀⠀⠀⠀⠀⠀⠀    ⠀⠀⠀⣠⠟⢁⣴⣿⣿⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣿⣿⣦⠈⢳⡄⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⣿⡇⠀⢀⣀⣤⣤⣤⣤⣀⡀⠀⢸⣿⣿⠀⠀⠀⠀⠀⠀⠀    ⠀⠀⣰⠏⢠⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣷⡀⢻⡄⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣔⢿⡿⠟⠛⠛⠻⢿⡿⣢⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀    ⠀⢰⡟⠀⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣷⠈⣿⡀⠀
⠀⠀⠀⠀⣀⣤⣶⣾⣿⣿⣿⣷⣤⣀⡀⢀⣀⣤⣾⣿⣿⣿⣷⣶⣤⡀⠀⠀⠀⠀    ⠀⣾⡇⢸⣿⣿⣿⣿⣿⣿⣿⣿⠟⣀⣤⣄⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⡄⢸⡇⠀
⠀⠀⢠⣾⣿⡿⠿⠿⠿⣿⣿⣿⣿⡿⠏⠻⢿⣿⣿⣿⣿⠿⠿⠿⢿⣿⣷⡀⠀⠀    ⠀⣿⠀⠘⠛⠛⠛⠛⠛⠛⠛⠃⢸⣿⣿⣿⣷⠀⠛⠛⠛⠛⠛⠛⠛⠛⠃⢸⡇⠀
⠀⢠⡿⠋⠁⠀⠀⢸⣿⡇⠉⠻⣿⠇⠀⠀⠸⣿⡿⠋⢰⣿⡇⠀⠀⠈⠙⢿⡄⠀    ⠀⢻⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⠿⠿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡇⠀
⠀⡿⠁⠀⠀⠀⠀⠘⣿⣷⡀⠀⠰⣿⣶⣶⣿⡎⠀⢀⣾⣿⠇⠀⠀⠀⠀⠈⢿⠀    ⠀⠸⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣶⣶⣶⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⠁⠀
⠀⡇⠀⠀⠀⠀⠀⠀⠹⣿⣷⣄⠀⣿⣿⣿⣿⠀⣠⣾⣿⠏⠀⠀⠀⠀⠀⠀⢸⠀    ⠀⠀⠹⣇⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀⠀⠀⠀⠀⣼⠃⠀⠀
⠀⠁⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⢇⣿⣿⣿⣿⡸⣿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠈⠀    ⠀⠀⠀⠘⢧⡀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀⠀⣠⡾⠁⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⣿⣿⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀    ⠀⠀⠀⠀⠈⠻⢦⣀⠀⠸⢿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠀⠀⣠⡾⠋⠀⠀⠀⠀⠀
⠀⠀⠀⠐⢤⣀⣀⢀⣀⣠⣴⣿⣿⠿⠋⠙⠿⣿⣿⣦⣄⣀⠀⠀⣀⡠⠂⠀⠀⠀    ⠀⠀⠀⠀⠀⠀⠀⠉⠛⠶⣦⣤⣀⣉⣉⣉⣁⣠⣤⣴⠶⠛⠁⠀ 
⠀⠀⠀⠀⠀⠈⠉⠛⠛⠛⠛⠉⠀⠀⠀⠀⠀⠈⠉⠛⠛⠛⠛⠋⠁⠀⠀⠀⠀⠀    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ⠈⠉⠉⠉⠉⠉⠉⠁⠀ ZONA v{version}⠀⠀⠀
{reset}"""
        print(banner)

    if args.command == "download":
        logger.info("- [Downloading ZONA archives and verifying checksums]\n")
        download.download_only(paths)

    if args.command == "setup":
        logger.info("- [Initializing ZONA modpack environment setup]\n")
        setup.run(paths)

    if args.command == "install":
        if not args.steam and path_ops.steam_installed():
            logger.info("- [Steam detected]")
            args.steam = utils.yes_or_no("Set up the Steam integration? [y/N] >>> ", default=False)
        if args.steam and steam.steam_running():
            logger.error("- [Steam is running: close it first, it would overwrite the library changes]")
            raise SystemExit(1)
        if not use_steam_install_dir(args, paths):
            raise SystemExit(1)
        if args.steam and not use_steam_prefix(args, paths):
            logger.error("- [Could not set up the Steam prefix, aborting]")
            raise SystemExit(1)
        logger.info("- [Initializing ZONA modpack installation]\n")
        modpack_source = setup.run(paths)
        install.run(paths, modpack_source)
        if args.steam and not use_steam_prefix(args, paths):
            logger.error("- [Could not set up the Steam prefix, aborting]")
            raise SystemExit(1)
        if args.steam and not steam.add_to_library(paths):
            logger.error("- [Failed to add Mod Organizer 2 to the Steam library]")
            raise SystemExit(1)

    if args.command == "mo2":
        logger.info("- [Running ZONA Mod Organizer 2]\n")
        mo2.run(paths)


    if args.command == "steam":
        logger.info("- [Adding Mod Organizer 2 to the Steam library]\n")
        if not use_steam_install_dir(args, paths):
            raise SystemExit(1)
        if not steam.add_to_library(paths):
            logger.error("- [Failed to add Mod Organizer 2 to the Steam library]")
            raise SystemExit(1)

    if args.command == "delete":
        # logger.info("- [Initializing ZONA modpack removal]\n")
        # delete.run(paths)
        pass


def steam_mode(args):
    """True when Steam integration is on: `zona install --steam` (or answered yes) or `zona steam`."""
    return args.command == "steam" or bool(getattr(args, "steam", False))


def use_steam_install_dir(args, paths):
    """In Steam mode, install into <Steam root>/steamapps/common/ZONA instead of config.toml's
    install_dir. An explicit -i always wins. Returns False if Steam can't be found."""
    if not steam_mode(args) or getattr(args, "install_dir", None):
        return True
    install_dir = steam.default_install_dir()
    if install_dir is None:
        return False
    paths["install_dir"] = install_dir
    logger.info(f"- [Steam mode: installing to '{install_dir}' (pass -i to choose another folder)]")
    return True


def use_steam_prefix(args, paths):
    """Point wine_prefix_dir at the prefix Steam uses for the shortcut. Returns True on success."""
    if args.proton_prefix:
        logger.warning("- [-p is ignored with --steam: Steam decides the prefix]")
        return False
    if args.install_dir:
        library = steam.find_library(paths["install_dir"])
        if library is None:
            logger.error(f"- ['{paths['install_dir']}' is not inside a Steam library]")
            return False
        logger.info(f"- [Steam library: {library}]")

    prefix = steam.shortcut_prefix(paths)
    if prefix is None:
        return False
    paths["wine_prefix_dir"] = prefix
    logger.info(f"- [Steam prefix: {prefix}]")
    return True


def restart_in_fhs():
    """On NixOS, re-run this same zona command inside steam-run (an FHS environment), which
    Proton's Wine needs. Does nothing elsewhere, or when already inside one."""
    if not path_ops.needs_fhs() or os.environ.get("ZONA_IN_FHS"):
        return
    steam_run = shutil.which("steam-run")
    if steam_run is None:
        logger.warning(
            "- [NixOS detected: Wine needs an FHS environment but 'steam-run' was not found. "
            "Enable programs.steam (or add steam-run) and run 'steam-run zona ...']"
        )
        return
    logger.info("- [NixOS detected: restarting inside steam-run (FHS environment)]")
    os.environ["ZONA_IN_FHS"] = "1"  # don't restart again inside steam-run
    os.execvp(steam_run, [steam_run, *sys.orig_argv])