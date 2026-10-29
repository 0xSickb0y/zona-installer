import os
import hashlib
from zona.core.log import logger


def verify_archives(TOML_CONFIG, ARCHIVES_DIR):
    """Check every downloaded file against the md5 in config.toml.
    Returns (verify_ok, {filename: True | False | None})."""
    print("Initiating MD5 Checksums")

    verify_ok = True
    checksum_results = {}
    for artifact in TOML_CONFIG["artifacts"]:
        if "one_of" in artifact:
            continue  # handled by resolve_one_of()
        for item in artifact.get("parts") or [artifact]:
            filename = item["filename"]
            file_path = os.path.join(ARCHIVES_DIR, filename)
            try:
                status = verify_md5(file_path, item["md5"])
            except FileNotFoundError:
                status = None
            checksum_results[filename] = status
            log_result(filename, item["md5"], status)
            if status is not True:
                verify_ok = False

    return (verify_ok, checksum_results)


def resolve_one_of(artifacts, ARCHIVES_DIR, group, skip=()):
    """Return the id of the first usable source in `group`, or None.

    A source is usable when all its files exist and match their md5.
    The single archive is tried before the multipart set (one file to extract).
    """
    sources = [a for a in artifacts if a.get("one_of") == group and a["id"] not in skip]
    sources.sort(key=lambda a: "parts" in a) # single file first

    for source in sources:
        for item in source.get("parts") or [source]:
            file_path = os.path.join(ARCHIVES_DIR, item["filename"])
            try:
                status = verify_md5(file_path, item["md5"])
            except FileNotFoundError:
                status = None
            log_result(item["filename"], item["md5"], status)
            if status is not True:
                break # this source is unusable, don't hash the rest of it
        else:
            return source["id"]
    return None


def verify_md5(file_path, expected_md5):
    """True if the file's md5 matches the expected one (compare lowercase)."""
    file_md5 = compute_md5(file_path)
    return file_md5.lower() == expected_md5.lower()


def compute_md5(file_path):
    """Return the md5 hex digest of a file. Read it in chunks: the files are large."""
    with open(file_path, "rb") as file:
        file_md5 = hashlib.file_digest(file, "md5")
    return file_md5.hexdigest()


def log_result(filename, md5, status):
    """Log one checksum result."""
    if status is True:
        logger.info(f"- [{md5} - {'OK':<7} - {filename}]")
    elif status is False:
        logger.error(f"- [{md5} - {'FAILED':<7} - {filename}]")
    else:
        logger.warning(f"- [{md5} - {'MISSING':<7} - {filename}]")