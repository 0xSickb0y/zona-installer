import shutil
import time
from pathlib import Path
from zona.core import config, utils
from zona.install import extract
from zona.core.log import logger
from zona.setup import hash_verification, path_ops, runner


TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]
GAME_EXE = "bin/AnomalyDX11.exe"  # TMP: for demo purposes
PROFILE_NAME = "Default" # TODO: change based on hardware detection
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def run(paths, modpack_source):
    start = time.perf_counter()
    completed = False
    print("\nStarting Extract and Install process")
    try:
        config.resolve_alternatives(ARTIFACTS, paths["archives_dir"])
        anomaly = next(a for a in ARTIFACTS if a["id"] == "anomaly")
        dest = Path(anomaly["dest"].format(**paths))

        if anomaly_installed(dest, anomaly["check_file"], anomaly["check_md5"]):
            logger.info(f"- [Anomaly already installed in '{dest}', skipping extraction]")
        elif not extract.extract_artifact(ARTIFACTS, "anomaly", paths):
            logger.error("- [Could not extract the Anomaly archive, aborting]")
            raise SystemExit(1)

        print()

        # Anomaly may need one first launch to generate the config/runtime files MO2 expects.
        if not path_ops.verify_existing_file(GAME_EXE, INSTALL_DIR=dest):
            logger.error(f"- [{GAME_EXE} not found inside '{dest}', aborting]")
            raise SystemExit(1)

        if anomaly_runtime_files_present(dest):
            logger.info("- [Anomaly runtime files already present; no first-launch step required]")
        else:
            logger.info("- [Launching Anomaly once to generate the runtime files needed by MO2]")
            if not utils.yes_or_no(
                "Anomaly has not generated its runtime files yet. Launch it once to create them, then close it and return here? [Y/n] >>>",
                default=True,
            ):
                logger.info("- [Skipped Anomaly launch; MO2 may need the first-run files generated later]")    
            elif not runner.run_exe(dest / GAME_EXE, dest, paths["wine_prefix_dir"], paths["runners_dir"], suppress_output=True): # TODO: --verbose option removes suppress_output=True
                logger.error("- [Could not launch the game, aborting]")
                raise SystemExit(1)

        exes_artifact = selected_exes_variant()
        exes_target = dest / "db" / "mods" / "00_modded_exes_gamedata.db0"
        if exes_target.exists():
            logger.info(f"- [Modded exes already installed in '{exes_target.parent}', skipping extraction]")
        else:
            path_ops.backup_original_bin(dest)
            logger.info(f"- [Extracting {exes_artifact['id']} ({exes_artifact['variant']})]")
            if not extract.extract_artifact(ARTIFACTS, exes_artifact["id"], paths):
                logger.error("- [Could not extract the selected exes variant, aborting]")
                raise SystemExit(1)

        clear_shader_cache(dest)

        hud_artifact = selected_hud_variant()
        if hud_artifact["variant"] == "clean":
            logger.warning(
                "- [Clean HUD requires using the SSS23.5 profile in mo2]"
            )

        # The HUD replaces Anomaly's own user.ltx / axr_options.ltx: keep the originals first,
        # then overwrite without asking. Never overwrite them if the backup failed.
        if not backup_runtime_config_files(dest):
            logger.error("- [Could not back up 'user.ltx' and 'axr_options.ltx', skipping the HUD]")
        elif not extract.extract_artifact(ARTIFACTS, hud_artifact["id"], paths, overwrite=True):
            logger.info("- [Skipped extraction of the selected HUD variant]")

        mo2 = next(a for a in ARTIFACTS if a["id"] == "mo2")
        mo2_dir = Path(mo2["dest"].format(**paths))
        if mo2_installed(mo2_dir):
            logger.info(f"- [Mod Organizer 2 already installed in '{mo2_dir}', skipping extraction]")
        elif not extract.extract_artifact(ARTIFACTS, "mo2", paths):
            logger.error("- [Could not extract Mod Organizer 2, aborting]")
            raise SystemExit(1)

        profiles_dir = mo2_dir / "profiles"
        if profiles_installed(profiles_dir):
            logger.info(f"- [ZONA profiles already installed in '{profiles_dir}', skipping extraction]")
        elif not extract.extract_artifact(ARTIFACTS, "profiles", paths):
            logger.error("- [Could not extract the ZONA profiles, aborting]")
            raise SystemExit(1)

        if modpack_installed(mo2_dir):
            logger.info(f"- [ZONA modpack already installed in '{mo2_dir}', skipping extraction]")
        elif not extract.extract_artifact(ARTIFACTS, modpack_source, paths):
            logger.error("- [Could not extract the ZONA modpack, aborting]")
            raise SystemExit(1)


        print()
        logger.info("- [Writing ModOrganizer2 .INI Files]")
        profile_name = default_profile_name(mo2_dir)
        if mo2_ini_files_present(mo2_dir) and not confirm_rewrite_ini(mo2_dir):
            logger.info(f"- [Keeping the existing MO2 INI files in '{mo2_dir}']")
        elif not write_mo2_configs(mo2_dir, dest, profile_name):
            logger.error("- [Could not write the Mod Organizer 2 config files, aborting]")
            raise SystemExit(1)

        completed = True
    finally:
        if completed:
            duration = time.perf_counter() - start
            print()
            logger.info(f"- [zona install completed in {duration:.2f}s]")
            print("Installation completed. Good Hunting S.T.A.L.K.E.R.!")
            print("run: 'zona mo2' to launch Mod Organizer 2.\n")


# TODO: move to proper module
def selected_exes_variant():
    """Return the chosen exes artifact for the current install."""
    choices = TOML_CONFIG["choices"]
    chosen = choices["exes"]["default"]
    return next(a for a in ARTIFACTS if a.get("group") == "exes" and a.get("variant") == chosen)


# TODO: move to proper module
def selected_hud_variant():
    """Return the chosen HUD artifact for the current install."""
    choices = TOML_CONFIG["choices"]
    chosen = choices["hud"]["default"]
    return next(a for a in ARTIFACTS if a.get("group") == "hud" and a.get("variant") == chosen)


# TODO: move to proper module
def backup_runtime_config_files(game_dir):
    """Back up critical Anomaly config files before applying modded EXEs or HUD overlays."""
    files = [
        Path(game_dir) / "appdata" / "user.ltx",
        Path(game_dir) / "gamedata" / "configs" / "axr_options.ltx",
    ]

    for file_path in files:
        if not file_path.exists():
            logger.info(f"- [No runtime config found at '{file_path}', skipping backup]")
            continue

        backup_path = Path(str(file_path) + ".bak")
        if backup_path.exists():
            logger.info(f"- [Backup already exists at '{backup_path}', keeping it]")
            continue

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"- [Backed up '{file_path}' to '{backup_path}']")
        except OSError as error:
            logger.error(f"- [Could not back up '{file_path}': {error}]")
            return False

    return True


# TODO: move to proper module
def clear_shader_cache(game_dir):
    """Delete the generated shader cache so the new EXEs rebuild it cleanly."""
    cache_dir = Path(game_dir) / "appdata" / "shaders_cache"
    if not cache_dir.exists():
        logger.info(f"- [No shader cache found at '{cache_dir}', skipping]")
        return True

    try:
        shutil.rmtree(cache_dir)
    except OSError as error:
        logger.error(f"- [Could not clear shader cache '{cache_dir}': {error}]")
        return False

    logger.info(f"- [Cleared shader cache at '{cache_dir}']")
    return True


# TODO: move to proper module
def default_profile_name(mo2_dir):
    """Return the installed MO2 profile to use, or the default fallback."""
    profiles_dir = mo2_dir / "profiles"
    if profiles_dir.exists():
        dirs = sorted(p.name for p in profiles_dir.iterdir() if p.is_dir())
        if dirs:
            return dirs[0]
    return PROFILE_NAME


# TODO: move to proper module
def mo2_ini_files_present(mo2_dir):
    """True if the standard MO2 INI files are already present in the MO2 folder."""
    return (mo2_dir / "ModOrganizer.ini").exists() and (mo2_dir / "nxmhandler.ini").exists()


def confirm_rewrite_ini(mo2_dir):
    """Ask whether to replace the existing ModOrganizer.ini (the old one is saved as .bak)."""
    ini = mo2_dir / "ModOrganizer.ini"
    print()
    question = f"'{ini}' already exists. Replace it with a fresh one? (a .bak copy is kept) [y/N] >>> "
    if not utils.yes_or_no(question, default=False):
        return False
    return path_ops.backup_file(ini)


# TODO: move to proper module
def anomaly_installed(dest, check_file, check_md5):
    """True if check_file exists in dest and its md5 matches."""
    if not path_ops.verify_existing_file(check_file, INSTALL_DIR=dest):
        return False
    if not hash_verification.verify_md5(dest / check_file, check_md5):
        logger.warning(f"- [{check_file} found but its md5 differs, reinstalling]")
        return False
    return True


# TODO: move to proper module
def mo2_installed(mo2_dir):
    """True if the MO2 executable is present (an INI alone doesn't count)."""
    return any((mo2_dir / name).exists() for name in ("ModOrganizer.exe", "ModOrganizer64.exe"))


# TODO: move to proper module
def profiles_installed(profiles_dir):
    """True if the ZONA profile folder already contains files."""
    return profiles_dir.exists() and any(profiles_dir.iterdir())


# TODO: move to proper module
def modpack_installed(mo2_dir):
    """True if the modpack has already been extracted into the MO2 mods directory."""
    mods_dir = mo2_dir / "mods"
    return mods_dir.exists() and any(mods_dir.iterdir())


# TODO: move to proper module
def anomaly_runtime_files_present(anomaly_dir):
    """True if the first-run Anomaly runtime markers exist in the Anomaly folder."""
    anomaly_dir = Path(anomaly_dir)
    return (anomaly_dir / "appdata" / "user.ltx").exists() or (anomaly_dir / "logs").exists()


# TODO: move to proper module
def write_mo2_configs(mo2_dir, anomaly_dir, profile_name):
    """Write ModOrganizer.ini and nxmhandler.ini into the MO2 folder.
    Paths use Wine's Z: drive, so MO2 finds them in any prefix."""
    game = "Z:" + str(Path(anomaly_dir).resolve())
    mo2 = "Z:" + str(Path(mo2_dir).resolve())
    game_win = game.replace("/", "\\")
    game_bytearray = game_win.replace("\\", "\\\\")
    values = {
        "PROFILE_NAME": profile_name,
        "PROFILE_NAME_BYTEARRAY": f"@ByteArray({profile_name})",
        "GAME_PATH": game,
        "GAME_PATH_WIN": game_win,
        "GAME_PATH_BYTEARRAY": f"@ByteArray({game_bytearray})",
        "ANOMALY_LAUNCHER": f"{game}/AnomalyLauncher.exe",
        "ANOMALY_BIN": f"{game}/bin",
        "EXPLORER_BIN": f"{mo2}/explorer++/Explorer++.exe",
        "EXPLORER_DIR": f"{mo2}/explorer++",
        "RECENT_DIR": f"{game}/bin",
    }
    files = {
        "ModOrganizer.ini": "ModOrganizer.ini",
        "nxmhandler.ini": "nxmhandler.ini",
    }
    for template, target in files.items():
        if not path_ops.render_template(TEMPLATES_DIR / template, mo2_dir / target, values):
            return False
    return True