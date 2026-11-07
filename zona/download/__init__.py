import time

from zona.core.log import logger
from zona.core import config

TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]


def _select_artifacts(artifacts, choices, hud=None, exes=None):
    """Keep only the chosen HUD/exes variants while preserving ungrouped artifacts."""
    chosen = {
        "hud": hud or choices["hud"]["default"],
        "exes": exes or choices["exes"]["default"],
    }
    return [a for a in artifacts if "group" not in a or a["variant"] == chosen[a["group"]]]


def download_only(paths):
    """Download the selected archives and validate their checksums without setting up Proton."""
    from zona.download import download
    from zona.setup import modpack, path_ops

    start = time.perf_counter()
    completed = False
    try:
        ARCHIVES_DIR = paths["archives_dir"]
        config.resolve_alternatives(ARTIFACTS, ARCHIVES_DIR)
        SELECTED_ARTIFACTS = [a for a in _select_artifacts(ARTIFACTS, TOML_CONFIG["choices"]) if a["id"] != "ge_proton"]

        # Download-only mode fetches both HUD options; install-time selection picks one later.
        for hud_artifact in ARTIFACTS:
            if hud_artifact.get("group") == "hud" and hud_artifact not in SELECTED_ARTIFACTS:
                SELECTED_ARTIFACTS.append(hud_artifact)

        # Download-only mode should not prompt about the install directory or Steam-managed paths.
        # It only needs the archive location to exist.
        if "failed" in path_ops.create_directories((ARCHIVES_DIR,)).values():
            logger.error("- [Could not prepare the archive directory, aborting]")
            raise SystemExit(1)

        # Same pipeline as `zona setup`: pick the modpack source, then fetch/verify each file on its own.
        modpack_source = modpack.choose_source(SELECTED_ARTIFACTS, ARCHIVES_DIR)
        to_fetch = [a for a in SELECTED_ARTIFACTS if "one_of" not in a or a["id"] == modpack_source]
        ok, results = download.ensure_archives(to_fetch, ARCHIVES_DIR)

        if not ok:
            modpack_source = modpack.fallback_to_multipart(SELECTED_ARTIFACTS, ARCHIVES_DIR, modpack_source, results)
            to_fetch = [a for a in SELECTED_ARTIFACTS if "one_of" not in a or a["id"] == modpack_source]
            ok = modpack_source is not None and all(
                results.get(item["filename"]) is True for a in to_fetch for item in a.get("parts") or [a]
            )
        if not ok:
            logger.error("- [Some archives are still missing or corrupted]")
            raise SystemExit(1)

        print()
        completed = True
        return True
    except SystemExit:
        raise
    except Exception as e:
        logger.exception(f"- [Unexpected error: {e}]")
        raise SystemExit(1)
    finally:
        if completed:
            duration = time.perf_counter() - start
            logger.info(f"- [zona download completed in {duration:.2f}s]")
