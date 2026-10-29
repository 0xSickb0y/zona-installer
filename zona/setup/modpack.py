from zona.core.log import logger
from zona.setup import download, hash_verification


def ensure_modpack(artifacts, ARCHIVES_DIR):
    """Return the id of a verified modpack source, or None.

    Tries the single archive first. If no source verifies, downloads the
    multipart set and verifies again. Runs after the md5 section.
    """
    source = hash_verification.resolve_one_of(artifacts, ARCHIVES_DIR, "modpack")
    if source is not None:
        return source

    logger.warning("- [No usable modpack archive, downloading the multipart set]")
    multipart = next(a for a in artifacts if a["id"] == "zona_modpack")
    ok, failed = download.download_artifact(multipart, ARCHIVES_DIR)
    if not ok:
        logger.error(f"- [Failed downloads ({len(failed)})]")
        for filename in failed:
            print(f"{'':9} - {filename}")
        return None

    source = hash_verification.resolve_one_of(
        artifacts, ARCHIVES_DIR, "modpack", skip=("zona_modpack_single",)
    )
    if source is None:
        logger.error("- [Multipart modpack failed verification]")
    return source