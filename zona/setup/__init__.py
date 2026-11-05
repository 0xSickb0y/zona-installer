import time
from pathlib import Path
from zona.core import config
from zona.core.log import logger
from zona.download import download as download_module
from zona.setup import hash_verification, modpack, path_ops, runner, proton

# Backwards-compatible import for internal code that still expects zona.setup.download
# while the implementation lives under zona.download.
download = download_module


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


def run(paths, skip_archive_cleanup=False):
    start = time.perf_counter()
    completed = False

    try:
        INSTALL_DIR = paths["install_dir"]
        ARCHIVES_DIR = paths["archives_dir"]
        WINE_PREFIX_DIR = paths["wine_prefix_dir"]
        RUNNERS_DIR = paths["runners_dir"]

        SELECTED_ARTIFACTS = [
            a for a in select_artifacts(
                ARTIFACTS, TOML_CONFIG["choices"]
            )
            if a["id"] != "ge_proton"
        ]

        existing_install = existing_install_detected(paths)

        if existing_install:
            logger.info(
                "- [Existing installation detected; skipping archive download]"
            )

            modpack_source = modpack.ensure_modpack(
                SELECTED_ARTIFACTS, ARCHIVES_DIR
            )

            if modpack_source is None:
                modpack_source = next(
                    a["id"] for a in SELECTED_ARTIFACTS
                    if a.get("one_of") == "modpack"
                )

            to_verify = [
                a for a in SELECTED_ARTIFACTS
                if "one_of" not in a or a["id"] == modpack_source
            ]

            # Verification will happen during directory preparation.
            verify_ok = None
            checksum_results = None

        else:
            # 1. Download archives
            download_ok, download_results = download.download_archives(
                SELECTED_ARTIFACTS, ARCHIVES_DIR
            )

            if not download_ok:
                failed_downloads = download_results["Failed"]

                logger.error(
                    f"- [Failed downloads ({len(failed_downloads)})]"
                )

                for filename in failed_downloads:
                    print(f"{'':9} - {filename}")

                raise SystemExit(1)

            # 2. Select modpack
            modpack_source = modpack.ensure_modpack(
                SELECTED_ARTIFACTS, ARCHIVES_DIR
            )

            if modpack_source is None:
                logger.error(
                    "- [Could not get a usable modpack archive, aborting]"
                )
                raise SystemExit(1)

            logger.info(
                f"- [Using modpack source: "
                f"{modpack.describe_source(SELECTED_ARTIFACTS, modpack_source)}]"
            )

            # 3. Determine artifacts to verify
            to_verify = [
                a for a in SELECTED_ARTIFACTS
                if "one_of" not in a or a["id"] == modpack_source
            ]

            # 4. Verify checksums
            print("\nInitiating MD5 Checksums")

            verify_ok, checksum_results = hash_verification.verify_archives(
                to_verify, ARCHIVES_DIR
            )

            if not verify_ok:
                logger.error(
                    "- [Checksum verification failed: "
                    "some archives are missing or corrupted]"
                )

                mismatched = [
                    name for name, status in checksum_results.items()
                    if status is False
                ]

                missing = [
                    name for name, status in checksum_results.items()
                    if status is None
                ]

                if mismatched:
                    logger.error(
                        f"- [Checksum mismatch ({len(mismatched)})]"
                    )
                    for filename in mismatched:
                        print(f"{'':9} - {filename}")

                if missing:
                    logger.error(
                        f"- [Missing archives ({len(missing)})]"
                    )
                    for filename in missing:
                        print(f"{'':9} - {filename}")

                # 5. Recover modpack if necessary
                modpack_source = modpack.recover_modpack(
                    SELECTED_ARTIFACTS,
                    ARCHIVES_DIR,
                    modpack_source,
                    checksum_results,
                )

                if modpack_source is None:
                    logger.error(
                        "- [Could not get a verified modpack archive, aborting]"
                    )
                    raise SystemExit(1)

                # Recovery may have changed the selected modpack.
                # Rebuild the verification set and verify it again.
                to_verify = [
                    a for a in SELECTED_ARTIFACTS
                    if "one_of" not in a or a["id"] == modpack_source
                ]

                verify_ok, checksum_results = (
                    hash_verification.verify_archives(
                        to_verify, ARCHIVES_DIR
                    )
                )

                if not verify_ok:
                    logger.error(
                        "- [Archive verification still failed after recovery]"
                    )
                    raise SystemExit(1)

            else:
                logger.info("- [All archives verified]")
                print()

        # 6. Verify/preserve archive cache and prepare directories.
        # Reuse checksum results when already available.
        dirs_ok, _ = path_ops.verify_and_create_directories(
            INSTALL_DIR,
            ARCHIVES_DIR,
            WINE_PREFIX_DIR.parent,
            RUNNERS_DIR,
            artifacts=to_verify,
            checksum_results=checksum_results,
            verify_ok=verify_ok,
        )

        if not dirs_ok:
            logger.error(
                "- [Could not prepare the installation directories, aborting]"
            )
            raise SystemExit(1)

        # 7. Ensure GE-Proton
        if proton.ensure_proton(ARTIFACTS, paths) is None:
            logger.error("- [Could not get GE-Proton, aborting]")
            raise SystemExit(1)

        # 8. Setup protontricks
        if not runner.setup_protontricks():
            logger.error("- [Could not set up protontricks, aborting]")
            raise SystemExit(1)

        # 9. Setup 7z
        if not runner.setup_7z():
            logger.error("- [Could not set up 7z, aborting]")
            raise SystemExit(1)

        # 10. Setup winetricks
        if not runner.setup_winetricks():
            logger.error("- [Could not set up winetricks, aborting]")
            raise SystemExit(1)

        # 11. Create Wine/Proton prefix
        if not runner.create_prefix(WINE_PREFIX_DIR, RUNNERS_DIR):
            logger.error("- [Could not set up wine prefix, aborting]")
            raise SystemExit(1)

        # 12. Install prefix components
        if not runner.install_components(
            WINE_PREFIX_DIR, WINE_COMPONENTS, RUNNERS_DIR
        ):
            logger.error("- [Could not install prefix components, aborting]")
            raise SystemExit(1)

        logger.info("- [Prefix components installed successfully]\n")

        completed = True
        return modpack_source

    except Exception as e:
        logger.exception(f"- [Unexpected error: {e}]")
        raise SystemExit(1)

    finally:
        if completed:
            duration = time.perf_counter() - start
            logger.info(
                f"- [zona setup completed in {duration:.2f}s]"
            )