import concurrent.futures
import time

from zona.core import config, utils
from zona.core.log import logger

TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]


def _select_artifacts(artifacts, choices, hud=None, exes=None):
    """Keep only the chosen HUD/exes variants while preserving ungrouped artifacts."""
    chosen = {
        "hud": hud or choices["hud"]["default"],
        "exes": exes or choices["exes"]["default"],
    }
    return [a for a in artifacts if "group" not in a or a["variant"] == chosen[a["group"]]]


def _artifacts_for_verification(artifacts, ARCHIVES_DIR):
    """Return the selected modpack source only when one valid alternative is present.
    This prevents a single valid modpack archive from being incorrectly flagged as missing
    just because the alternative multipart or single-file source is absent.
    """
    selected = [a for a in artifacts if a["id"] != "ge_proton"]
    modpack_sources = [a for a in selected if a.get("one_of") == "modpack"]
    if not modpack_sources:
        return selected

    from zona.setup import modpack

    source_id = modpack.resolve_one_of(ARTIFACTS, ARCHIVES_DIR, "modpack")
    if source_id is None:
        return selected

    return [a for a in selected if "one_of" not in a or a["id"] == source_id]


def download_only(paths):
    """Download the selected archives and validate their checksums without setting up Proton."""
    from zona.download import download as download_helpers
    from zona.setup import hash_verification, path_ops

    start = time.perf_counter()
    completed = False
    downloaded_any = False
    try:
        ARCHIVES_DIR = paths["archives_dir"]
        INSTALL_DIR = paths["install_dir"]
        SELECTED_ARTIFACTS = [a for a in _select_artifacts(ARTIFACTS, TOML_CONFIG["choices"]) if a["id"] != "ge_proton"]
        VERIFY_ARTIFACTS = _artifacts_for_verification(SELECTED_ARTIFACTS, ARCHIVES_DIR)

        # Download-only mode should fetch both HUD options by default; install-time selection can be
        # implemented later via a CLI switch without adding extra complexity here.
        for hud_artifact in ARTIFACTS:
            if hud_artifact.get("group") == "hud" and hud_artifact not in VERIFY_ARTIFACTS:
                VERIFY_ARTIFACTS.append(hud_artifact)

        # Download-only mode should not prompt about the install directory or Steam-managed paths.
        # It only needs the archive location to exist.
        create_results = path_ops.create_directories((ARCHIVES_DIR,))
        if "failed" in create_results.values():
            logger.error("- [Could not prepare the archive directory, aborting]")
            raise SystemExit(1)

        print("Initiating MD5 Checksums")
        verify_ok, checksum_results = hash_verification.verify_archives(VERIFY_ARTIFACTS, ARCHIVES_DIR)
        if verify_ok:
            logger.info("- [All archives verified]")
            print()
            return True

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

        missing_or_bad = [name for name, status in checksum_results.items() if status is not True]
        if not missing_or_bad:
            logger.warning("- [No missing or corrupted archives detected, but verification still failed]")
            raise SystemExit(1)

        if not utils.yes_or_no("Download the missing or corrupted archives? [y/N] >>>", default=False):
            raise SystemExit(1)

        items = []
        for artifact in VERIFY_ARTIFACTS:
            for item in artifact.get("parts") or [artifact]:
                if item["filename"] in missing_or_bad:
                    items.append(item)

        if not items:
            logger.error("- [No missing or corrupted archive entries matched the verification results]")
            raise SystemExit(1)

        pseudo_artifact = {"parts": items}
        downloaded_any = True
        threads = min(8, max(2, len(items)))
        logger.info(f"- [Fetching archives ({threads} threads)]")

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            futures = []
            for item in items:
                fut = pool.submit(download_helpers.download_file, item["url"], item["filename"], ARCHIVES_DIR)
                futures.append(fut)

            failed = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - suited to runtime fetch failures
                    logger.error(f"- [Download failed: {exc}]")
                    failed.append("<unknown>")

        if failed:
            logger.error(f"- [Failed downloads ({len(failed)})]")
            raise SystemExit(1)

        print()
        verify_ok, checksum_results = hash_verification.verify_archives([pseudo_artifact], ARCHIVES_DIR)
        if not verify_ok:
            logger.error("- [Some archives still failed verification after download]")
            raise SystemExit(1)

        logger.info("- [All archives verified]")
        print()
        completed = True
        return True
    except Exception as e:
        logger.exception(f"- [Unexpected error: {e}]")
        raise SystemExit(1)
    finally:
        if completed and downloaded_any:
            duration = time.perf_counter() - start
            logger.info(f"- [zona download completed in {duration:.2f}s]")
