import time
from pathlib import Path
from zona.core import config
from zona.core.log import logger
from zona.setup import download, hash_verification, modpack, path_ops, runner, proton


TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]
WINE_COMPONENTS = TOML_CONFIG["wine"]["components"]


def select_artifacts(artifacts, choices, hud=None, exes=None):
    """Keep only the chosen HUD/exes variants while preserving ungrouped artifacts."""
    chosen = {
        "hud": hud or choices["hud"]["default"],
        "exes": exes or choices["exes"]["default"],
    }
    return [a for a in artifacts if "group" not in a or a["variant"] == chosen[a["group"]]]


def existing_install_detected(paths):
    """True if the prefix already contains the core install state we care about."""
    wine_prefix = Path(paths["wine_prefix_dir"])
    if not wine_prefix.exists():
        return False

    anomaly_dir = wine_prefix / "drive_c" / "anomaly"
    mo2_dir = wine_prefix / "drive_c" / "mo2"
    profiles_dir = mo2_dir / "profiles"
    mods_dir = mo2_dir / "mods"

    has_anomaly = (anomaly_dir / "AnomalyLauncher.exe").exists()
    has_mo2 = any((mo2_dir / name).exists() for name in ("ModOrganizer.exe", "ModOrganizer64.exe"))
    has_profiles = profiles_dir.exists() and any(profiles_dir.iterdir())
    has_modpack = mods_dir.exists() and any(mods_dir.iterdir())

    return has_anomaly and has_mo2 and has_profiles and has_modpack


def run(paths):
    start = time.perf_counter()
    completed = False
    try:
        INSTALL_DIR = paths["install_dir"]
        ARCHIVES_DIR = paths["archives_dir"]
        WINE_PREFIX_DIR = paths["wine_prefix_dir"]
        RUNNERS_DIR = paths["runners_dir"]
        SELECTED_ARTIFACTS = [a for a in select_artifacts(ARTIFACTS, TOML_CONFIG["choices"]) if a["id"] != "ge_proton"]

        dirs_ok, _ = path_ops.verify_and_create_directories(INSTALL_DIR, ARCHIVES_DIR, WINE_PREFIX_DIR.parent, RUNNERS_DIR)
        if not dirs_ok:
            logger.error("- [Could not prepare the installation directories, aborting]")
            raise SystemExit(1)

        if existing_install_detected(paths):
            logger.info("- [Existing installation detected; skipping archive download and checksum verification]")
            modpack_source = next(a["id"] for a in SELECTED_ARTIFACTS if a.get("one_of") == "modpack")
            verify_ok = True
            checksum_results = {}
        else:
            download_ok, download_results = download.download_archives(SELECTED_ARTIFACTS, ARCHIVES_DIR)
            if not download_ok:
                failed_downloads = download_results["Failed"]
                logger.error(f"- [Failed downloads ({len(failed_downloads)})]")
                for filename in failed_downloads:
                    print(f"{'':9} - {filename}")
                raise SystemExit(1)

            modpack_source = modpack.ensure_modpack(SELECTED_ARTIFACTS, ARCHIVES_DIR)  # existence only, no hashing
            if modpack_source is None:
                logger.error("- [Could not get a usable modpack archive, aborting]")
                raise SystemExit(1)
            logger.info(f"- [Using modpack source: {modpack.describe_source(SELECTED_ARTIFACTS, modpack_source)}]")

            # everything that is always installed, plus only the chosen modpack source
            to_verify = [a for a in SELECTED_ARTIFACTS if "one_of" not in a or a["id"] == modpack_source]
            print("\nInitiating MD5 Checksums")
            verify_ok, checksum_results = hash_verification.verify_archives(to_verify, ARCHIVES_DIR)

        if not verify_ok:
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

            modpack_source = modpack.recover_modpack(SELECTED_ARTIFACTS, ARCHIVES_DIR, modpack_source, checksum_results)
            if modpack_source is None:
                logger.error("- [Could not get a verified modpack archive, aborting]")
                # raise SystemExit(1) TODO: uncomment after runner testing is done
        else:
            logger.info("- [All archives verified]")
            print()

        if proton.ensure_proton(ARTIFACTS, paths) is None:
              logger.error("- [Could not get GE-Proton, aborting]")
              raise SystemExit(1)

        if not runner.setup_protontricks():
            logger.error("- [Could not set up protontricks, aborting]")
            raise SystemExit(1)

        if not runner.setup_7z():
            logger.error("- [Could not set up 7z, aborting]")
            raise SystemExit(1)
        
        if not runner.create_prefix(WINE_PREFIX_DIR, RUNNERS_DIR):
            logger.error("- [Could not set up wine prefix, aborting]")
            raise SystemExit(1)

        if not runner.install_components(WINE_PREFIX_DIR, WINE_COMPONENTS, RUNNERS_DIR):
            logger.error("- [Could not install prefix components, aborting]")
            raise SystemExit(1)
        else:
            logger.info("- [Prefix components installed successfully]\n")

        completed = True
        return modpack_source
    except Exception as e:
        logger.exception(f"- [Unexpected error: {e}]")
        raise SystemExit(1)
    finally:
        if completed:
            duration = time.perf_counter() - start
            logger.info(f"- [zona setup completed in {duration:.2f}s]")