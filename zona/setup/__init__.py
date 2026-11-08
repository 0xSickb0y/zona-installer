import time
from pathlib import Path
from zona.core import config
from zona.core.log import logger
from zona.download import download as download_module
from zona.setup import modpack, path_ops, runner, proton

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
    """True if the install folder already contains the core install state we care about."""
    anomaly = next(a for a in ARTIFACTS if a["id"] == "anomaly")
    mo2 = next(a for a in ARTIFACTS if a["id"] == "mo2")
    anomaly_dir = Path(anomaly["dest"].format(**paths))
    mo2_dir = Path(mo2["dest"].format(**paths))
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
        config.resolve_alternatives(ARTIFACTS, ARCHIVES_DIR)

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

            modpack_source = modpack.choose_source(
                SELECTED_ARTIFACTS, ARCHIVES_DIR
            )

            to_verify = [
                a for a in SELECTED_ARTIFACTS
                if "one_of" not in a or a["id"] == modpack_source
            ]

            # Verification will happen during directory preparation.
            verify_ok = None
            checksum_results = None

        else:
            # 1. Pick the modpack source from what is on disk (no hashing yet)
            modpack_source = modpack.choose_source(
                SELECTED_ARTIFACTS, ARCHIVES_DIR
            )
            to_verify = [
                a for a in SELECTED_ARTIFACTS
                if "one_of" not in a or a["id"] == modpack_source
            ]

            if "failed" in path_ops.create_directories((ARCHIVES_DIR,)).values():
                logger.error("- [Could not prepare the archive directory, aborting]")
                raise SystemExit(1)

            # 2. Per file: missing -> download, present -> hash, corrupted -> replace (asked once).
            #    Each fetched file is verified on its own; nothing is hashed twice.
            verify_ok, checksum_results = download.ensure_archives(
                to_verify, ARCHIVES_DIR
            )

            # 3. The single modpack archive has no download URL; if it is unusable, use the multipart set.
            if not verify_ok:
                modpack_source = modpack.fallback_to_multipart(
                    SELECTED_ARTIFACTS, ARCHIVES_DIR, modpack_source, checksum_results
                )
                if modpack_source is None:
                    logger.error("- [Could not get a usable modpack archive, aborting]")
                    raise SystemExit(1)

                to_verify = [
                    a for a in SELECTED_ARTIFACTS
                    if "one_of" not in a or a["id"] == modpack_source
                ]
                verify_ok = all(
                    checksum_results.get(item["filename"]) is True
                    for a in to_verify for item in a.get("parts") or [a]
                )
                if not verify_ok:
                    logger.error("- [Some archives are still missing or corrupted, aborting]")
                    raise SystemExit(1)

            logger.info(
                f"- [Using modpack source: "
                f"{modpack.describe_source(SELECTED_ARTIFACTS, modpack_source)}]"
            )
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

        # 7. Pick the Proton to use (-r, menu, or download GE-Proton)
        if proton.ensure_proton(ARTIFACTS, paths) is None:
            logger.error("- [Could not get a Proton runner, aborting]")
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
        if not runner.create_prefix(WINE_PREFIX_DIR, paths):
            logger.error("- [Could not set up wine prefix, aborting]")
            raise SystemExit(1)

        # 12. Install prefix components
        if not runner.install_components(
            WINE_PREFIX_DIR, WINE_COMPONENTS, paths
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