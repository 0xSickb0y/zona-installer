from zona.core.log import logger
from zona.download import download
from zona.setup import path_ops

MULTIPART_ID = "zona_modpack"


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


def choose_source(artifacts, ARCHIVES_DIR):
    """Pick the modpack source before anything is hashed: whichever source is fully on disk,
    otherwise the multipart set (the only one with a download URL)."""
    return resolve_one_of(artifacts, ARCHIVES_DIR, "modpack") or MULTIPART_ID


def fallback_to_multipart(artifacts, ARCHIVES_DIR, source_id, results):
    """Called when the chosen modpack source failed in download.ensure_archives().
    The single archive can't be re-downloaded, so switch to the multipart set and fetch/verify
    only its parts. Updates `results`; returns the usable source id, or None."""
    source = next(a for a in artifacts if a["id"] == source_id)
    if all(results.get(i["filename"]) is True for i in source.get("parts") or [source]):
        return source_id
    if source_id == MULTIPART_ID:
        return None

    logger.warning(f"- [{describe_source(artifacts, source_id)} is unusable, using the multipart modpack instead]")
    for item in source.get("parts") or [source]:
        results.pop(item["filename"], None)  # the single archive no longer matters
    multipart = next(a for a in artifacts if a["id"] == MULTIPART_ID)
    ok, multipart_results = download.ensure_archives([multipart], ARCHIVES_DIR)
    results.update(multipart_results)
    return MULTIPART_ID if ok else None
