from zona.core import utils
from zona.core.log import logger
from zona.setup import download, hash_verification, path_ops


def describe_source(artifacts, source_id):
    """Human-readable label for a modpack source id."""
    source = next(a for a in artifacts if a["id"] == source_id)
    parts = source.get("parts") or [source]
    if len(parts) == 1:
        return parts[0]["filename"]
    return f"{parts[0]['filename']} (+ {len(parts) - 1} parts)"


def resolve_one_of(artifacts, ARCHIVES_DIR, group):
    """Id of the first source in `group` whose files all exist (no hashing), or None.
    The single archive is tried before the multipart set."""
    sources = [a for a in artifacts if a.get("one_of") == group]
    sources.sort(key=lambda a: "parts" in a)  # single file first
    for source in sources:
        items = source.get("parts") or [source]
        if all(path_ops.verify_existing_file(i["filename"], ARCHIVES_DIR=ARCHIVES_DIR) for i in items):
            return source["id"]
    return None


def ensure_modpack(artifacts, ARCHIVES_DIR):
    """Id of a modpack source whose files all exist, downloading the multipart set if none does."""
    source = resolve_one_of(artifacts, ARCHIVES_DIR, "modpack")
    if source is not None:
        return source

    logger.warning("- [No modpack archive found, downloading the multipart set]")
    multipart = next(a for a in artifacts if a["id"] == "zona_modpack")
    ok, failed = download.download_artifact(multipart, ARCHIVES_DIR)
    if not ok:
        logger.error(f"- [Failed downloads ({len(failed)})]")
        for filename in failed:
            print(f"{'':9} - {filename}")
        return None
    return multipart["id"]


def recover_modpack(artifacts, ARCHIVES_DIR, source_id, checksum_results):
    """Called after the md5 check. If the chosen modpack source has bad or missing
    files, offer to download the multipart set. Returns a verified source id, or None."""
    source = next(a for a in artifacts if a["id"] == source_id)
    names = [i["filename"] for i in source.get("parts") or [source]]
    bad = [name for name in names if checksum_results.get(name) is not True]
    if not bad:
        return source_id

    question = "Download the multipart modpack (bad or missing parts only)? [y/N] >>> "
    if not utils.yes_or_no(question, default=False):
        return None

    path_ops.remove_files(ARCHIVES_DIR, bad)  # so a bad file is fetched again
    multipart = next(a for a in artifacts if a["id"] == "zona_modpack")
    ok, failed = download.download_artifact(multipart, ARCHIVES_DIR)
    if not ok:
        logger.error(f"- [Failed downloads ({len(failed)})]")
        for filename in failed:
            print(f"{'':9} - {filename}")
        return None

    # hash only the parts that haven't been verified yet
    unverified = {"parts": [p for p in multipart["parts"] if checksum_results.get(p["filename"]) is not True]}
    verify_ok, _ = hash_verification.verify_archives([unverified], ARCHIVES_DIR)
    if not verify_ok:
        logger.error("- [The multipart modpack failed verification again]")
        return None
    return multipart["id"]