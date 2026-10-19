from zona.core import config
from zona.core.log import logger
from zona.setup import download, hash_verification, path_ops

TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]
INSTALL_DIR = path_ops.expand_var_and_user(TOML_CONFIG["defaults"]["install_dir"])
ARCHIVES_DIR = path_ops.expand_var_and_user(TOML_CONFIG["defaults"]["archives_dir"])

def run():
    dirs_ok, _ = path_ops.verify_and_create_directories(INSTALL_DIR, ARCHIVES_DIR)
    if not dirs_ok:
        logger.error("- [Could not prepare the installation directories, aborting]")
        raise SystemExit(1)

    download_ok, download_results = download.download_archives(ARTIFACTS, ARCHIVES_DIR)
    if not download_ok:
        failed_downloads = download_results["Failed"]
        logger.error(f"- [Failed downloads ({len(failed_downloads)})]")
        for filename in failed_downloads:
            print(f"{'':9} - {filename}")
        raise SystemExit(1)

    verify_ok, checksum_results = hash_verification.verify_archives(TOML_CONFIG, ARCHIVES_DIR)
    if verify_ok:
        logger.info("- [All archives verified]")
    else:
        logger.error("- [Checksum verification failed: some archives are missing or corrupted]")
        mismatched = [name for name, status in checksum_results.items() if status is False]
        missing = [name for name, status in checksum_results.items() if status is None]

        if mismatched:
            logger.error(f"- [Checksum mismatch ({len(mismatched)})]")
            for filename in mismatched:
                print(f"{'':9} - {filename}")
        if missing:
            logger.error(f"- [Missing archives ({len(missing)})]")
            for filename in missing:
                print(f"{'':9} - {filename}")
        raise SystemExit(1)

    # TODO:
        # install wine / proton / umu
        # cleaning functions