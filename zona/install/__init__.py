from pathlib import Path
from zona.core import config
from zona.install import extract
from zona.core.log import logger
from zona.setup import hash_verification, path_ops, runner


TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]
GAME_EXE = "bin/AnomalyDX11.exe"  # TMP: for demo purposes


def run(paths, modpack_source):
    anomaly = next(a for a in ARTIFACTS if a["id"] == "anomaly")
    dest = Path(anomaly["dest"].format(**paths))

    if anomaly_installed(dest, anomaly["check_file"], anomaly["check_md5"]):
        logger.info(f"- [Anomaly already installed in '{dest}', skipping extraction]")
    elif not extract.extract_artifact(ARTIFACTS, "anomaly", paths):
        logger.error("- [Could not extract the Anomaly archive, aborting]")
        raise SystemExit(1)

    # TODO: add is_installed() for mo2 and ZONA

    # order matters: later archives overwrite earlier ones (7z runs with -y)
    if not extract.extract_artifact(ARTIFACTS, "mo2", paths):
        logger.error("- [Could not extract Mod Organizer 2, aborting]")
        raise SystemExit(1)

    if not extract.extract_artifact(ARTIFACTS, modpack_source, paths):
        logger.error("- [Could not extract the ZONA modpack, aborting]")
        raise SystemExit(1)

    if not path_ops.verify_existing_file(GAME_EXE, INSTALL_DIR=dest):
        logger.error(f"- [{GAME_EXE} not found inside '{dest}', aborting]")
        raise SystemExit(1)

    # TMP: for demo purposes
    if not runner.run_exe(dest / GAME_EXE, dest, paths["wine_prefix_dir"]):
        logger.error("- [Could not launch the game, aborting]")
        raise SystemExit(1)


def anomaly_installed(dest, check_file, check_md5):
    """True if check_file exists in dest and its md5 matches."""
    if not path_ops.verify_existing_file(check_file, INSTALL_DIR=dest):
        return False
    if not hash_verification.verify_md5(dest / check_file, check_md5):
        logger.warning(f"- [{check_file} found but its md5 differs, reinstalling]")
        return False
    return True
