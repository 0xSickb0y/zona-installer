from pathlib import Path
from zona.core import config
from zona.core.log import logger
from zona.setup import hash_verification, path_ops, runner
from zona.install import extract


TOML_CONFIG = config.read_toml_configs()
DEFAULTS = {key: path_ops.expand_var_and_user(value) for key, value in TOML_CONFIG["defaults"].items()}
WINE_PREFIX_DIR = DEFAULTS["wine_prefix_dir"]


def anomaly_installed(dest, check_file, check_md5):
    """True if check_file exists in dest and its md5 matches."""
    if not path_ops.verify_existing_file(check_file, INSTALL_DIR=dest):
        return False
    if not hash_verification.verify_md5(dest / check_file, check_md5):
        logger.warning(f" - [{check_file} found but its md5 differs, reinstalling]")
        return False
    return True


def run():
    anomaly = next(a for a in TOML_CONFIG["artifacts"] if a["id"] == "anomaly")
    dest = Path(anomaly["dest"].format(**DEFAULTS))

    if anomaly_installed(dest, anomaly["check_file"], anomaly["check_md5"]):
        logger.info(f"- [Anomaly already installed in '{dest}', skipping extraction]")
    elif not extract.extract_archive(anomaly["filename"], DEFAULTS["archives_dir"], dest):
        logger.error("- [Could not extract the Anomaly archive, aborting]")
        raise SystemExit(1)

    if not path_ops.verify_existing_file(GAME_EXE, INSTALL_DIR=dest):
        logger.error(f"- [{GAME_EXE} not found inside '{dest}', aborting]")
        raise SystemExit(1)
