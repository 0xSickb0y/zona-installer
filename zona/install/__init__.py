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
    anomaly = next(a for a in ARTIFACTS if a["id"] == "anomaly")
    dest = Path(anomaly["dest"].format(**paths))

    if anomaly_installed(dest, anomaly["check_file"], anomaly["check_md5"]):
        logger.info(f"- [Anomaly already installed in '{dest}', skipping extraction]")
    elif not extract.extract_artifact(ARTIFACTS, "anomaly", paths):
        logger.error("- [Could not extract the Anomaly archive, aborting]")
        raise SystemExit(1)

    mo2_dir = Path(paths["wine_prefix_dir"]) / "drive_c" / "mo2"
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

    # Anomaly may need one first launch to generate the config/runtime files MO2 expects.
    if not path_ops.verify_existing_file(GAME_EXE, INSTALL_DIR=dest):
        logger.error(f"- [{GAME_EXE} not found inside '{dest}', aborting]")
        raise SystemExit(1)

    if anomaly_runtime_files_present(paths["wine_prefix_dir"]):
        logger.info("- [Anomaly runtime files already present; no first-launch step required]")
    else:
        logger.info("- [Launching Anomaly once to generate the runtime files needed by MO2]")
        if not utils.yes_or_no(
            "Anomaly has not generated its runtime files yet. Launch it once to create them, then close it and return here? [Y/n] >>>",
            default=True,
        ):
            logger.info("- [Skipped Anomaly launch; MO2 may need the first-run files generated later]")
        elif not runner.run_exe(dest / GAME_EXE, dest, paths["wine_prefix_dir"]):
            logger.error("- [Could not launch the game, aborting]")
            raise SystemExit(1)

    exes_artifact = selected_exes_variant()
    exes_target = Path(paths["wine_prefix_dir"]) / "drive_c" / "anomaly" / "db" / "mods" / "00_modded_exes_gamedata.db0"
    if exes_target.exists():
        logger.info(f"- [Modded exes already installed in '{exes_target.parent}', skipping extraction]")
    else:
        logger.info(f"- [Extracting {exes_artifact['id']} ({exes_artifact['variant']})]")
        if not extract.extract_artifact(ARTIFACTS, exes_artifact["id"], paths):
            logger.error("- [Could not extract the selected exes variant, aborting]")
            raise SystemExit(1)

    print()
    logger.info("- [Writing ModOrganizer2 .INI Files]")
    mo2_dir = Path(paths["wine_prefix_dir"]) / "drive_c" / "mo2"
    profile_name = default_profile_name(mo2_dir)
    if not write_mo2_configs(mo2_dir, profile_name):
        logger.error("- [Could not write the Mod Organizer 2 config files, aborting]")
        raise SystemExit(1)


# TODO: move to proper module
def selected_exes_variant():
    """Return the chosen exes artifact for the current install."""
    choices = TOML_CONFIG["choices"]
    chosen = choices["exes"]["default"]
    return next(a for a in ARTIFACTS if a.get("group") == "exes" and a.get("variant") == chosen)

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
    """True if MO2 appears to already be installed in this prefix."""
    return any((mo2_dir / name).exists() for name in ("ModOrganizer.exe", "ModOrganizer64.exe", "ModOrganizer.ini"))


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
def anomaly_runtime_files_present(wine_prefix_dir):
    """True if the first-run Anomaly runtime markers exist in the prefix."""
    drive_c = Path(wine_prefix_dir) / "drive_c"
    anomaly_dirs = [drive_c / "Anomaly", drive_c / "anomaly"]

    for anomaly_dir in anomaly_dirs:
        if not anomaly_dir.exists():
            continue
        candidate_files = [
            anomaly_dir / "appdata" / "user.ltx",
            anomaly_dir / "logs",
        ]
        if any(path.exists() for path in candidate_files):
            return True

    return False


# TODO: move to proper module
def write_mo2_configs(mo2_dir, profile_name):
    """Write ModOrganizer.ini and nxmhandler.ini into the MO2 folder."""
    values = {"BASE_PATH": "C:", "PROFILE_NAME": profile_name}
    files = {
        "ModOrganizer.ini": "ModOrganizer.ini",
        "nxmhandler.ini": "nxmhandler.ini",
    }
    for template, target in files.items():
        if not path_ops.render_template(TEMPLATES_DIR / template, mo2_dir / target, values):
            return False
    return True