import os
import sys
import shutil
from pathlib import Path
from zona import mo2
from zona import keybinds
from zona.mo2 import stylesheet
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
    if getattr(args, "runner", None) and getattr(args, "runners_dir", None):
        logger.warning("- [-s is ignored when -r is given: the -r runner is used]")
    # --clean-hud / --bhs-hud, else config.toml's default (clean)
    paths["hud"] = getattr(args, "hud", None) or config.read_toml_configs()["choices"]["hud"]["default"]
    # --modded-exes regular|mt, else config.toml's default (regular)
    paths["exes"] = getattr(args, "modded_exes", None) or config.read_toml_configs()["choices"]["exes"]["default"]

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
        logger.info("- [Initializing ZONA modpack installation]\n")
        if args.steam and args.proton_prefix:
            logger.error("- [-p can't be combined with --steam: Steam decides the prefix (compatdata/<appid>)]")
            raise SystemExit(1)
        if not args.steam and not args.proton_prefix and path_ops.steam_installed():
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
        modpack_source = setup.run(paths)
        install.run(paths, modpack_source)
        if args.mo2_stylesheet and not stylesheet.install_stylesheet(mo2_dir(paths)):
            logger.error("- [Could not install the MO2 stylesheet]")
            raise SystemExit(1)
        if args.steam and not steam.add_to_library(paths):
            logger.error("- [Failed to add Mod Organizer 2 to the Steam library]")
            raise SystemExit(1)

    if args.command == "mo2":
        logger.info("- [Running ZONA Mod Organizer 2]\n")
        if not args.proton_prefix and not use_existing_steam_prefix(paths):
            raise SystemExit(1)
        if args.hud and not install.apply_hud(paths):  # only when --clean-hud/--bhs-hud is given
            logger.error("- [Could not apply the selected HUD]")
            raise SystemExit(1)
        if args.mo2_stylesheet and not stylesheet.install_stylesheet(mo2_dir(paths)):
            logger.error("- [Could not install the MO2 stylesheet]")
            raise SystemExit(1)
        mo2.run(paths)


    if args.command == "steam":
        logger.info("- [Adding Mod Organizer 2 to the Steam library]\n")
        if not use_steam_install_dir(args, paths):
            raise SystemExit(1)
        if not use_steam_prefix(args, paths):
            logger.error("- [Could not set up the Steam prefix, aborting]")
            raise SystemExit(1)
        if not steam.add_to_library(paths):
            logger.error("- [Failed to add Mod Organizer 2 to the Steam library]")
            raise SystemExit(1)

    if args.command == "stylesheet":
        logger.info("- [Installing the S.T.A.L.K.E.R. Mod Organizer 2 stylesheet]\n")
        if not stylesheet.install_stylesheet(mo2_dir(paths)):
            logger.error("- [Could not install the MO2 stylesheet]")
            raise SystemExit(1)

    if args.command == "keybinds":
        if not keybinds.run():
            raise SystemExit(1)

    if args.command == "delete":
        # logger.info("- [Initializing ZONA modpack removal]\n")
        # delete.run(paths)
        logger.error("- ['zona delete' is not implemented yet]")
        raise SystemExit(1)


def mo2_dir(paths):
    """The MO2 folder of the install, from the mo2 artifact's dest in config.toml."""
    mo2 = next(a for a in config.read_toml_configs()["artifacts"] if a["id"] == "mo2")
    return Path(mo2["dest"].format(**paths))


def use_existing_steam_prefix(paths):
    """If this install was added to Steam, run in the shortcut's prefix: it is the one zona set up.
    Returns False when Steam has the shortcut but its prefix is gone (e.g. removed with the game).
    Without a shortcut the default prefix is kept."""
    if path_ops.find_steam_root() is None:
        return True
    prefix = steam.shortcut_prefix(paths)
    if prefix is None:
        return True
    if (prefix / "drive_c").is_dir():
        paths["wine_prefix_dir"] = prefix
        logger.info(f"- [Using the Steam shortcut's prefix: {prefix}]")
        return True
    if steam.has_shortcut(mo2_dir(paths) / "ModOrganizer.exe"):
        logger.error(f"- [ZONA is in your Steam library, but its Wine prefix is missing: '{prefix.parent}']")
        logger.error(f"- [Steam deletes it when the game is removed. Rebuild it with: "
                     f"zona install -i '{paths['install_dir']}' --steam]")
        return False
    return True


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
    """Point wine_prefix_dir at the shortcut's prefix, stored in the install's Steam library.

    Steam always looks for a shortcut's prefix in <Steam root>/steamapps/compatdata/<appid>.
    When ZONA is installed in another library (-i on another drive), the prefix lives in that
    library's compatdata and Steam's location becomes a symlink to it. Returns True on success."""
    if args.proton_prefix:
        logger.error("- [-p can't be used with the Steam integration: Steam decides the prefix (compatdata/<appid>)]")
        return False

    steam_prefix = steam.shortcut_prefix(paths)  # <Steam root>/steamapps/compatdata/<appid>/pfx
    if steam_prefix is None:
        return False
    root = path_ops.find_steam_root()

    library = root
    if args.install_dir:
        library = steam.find_library(paths["install_dir"])
        if library is None:
            logger.error(f"- ['{paths['install_dir']}' is not inside a Steam library]")
            return False
        logger.info(f"- [Steam library: {library}]")

    prefix = steam_prefix
    if Path(library).resolve() != Path(root).resolve():
        compat_dir = Path(library) / "steamapps" / "compatdata" / steam_prefix.parent.name
        if not steam.place_prefix(steam_prefix.parent, compat_dir):
            return False
        prefix = compat_dir / "pfx"

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