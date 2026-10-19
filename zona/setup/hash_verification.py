import os
import hashlib
from zona.core.log import logger


def verify_archives(TOML_CONFIG, ARCHIVES_DIR):
    """Check every downloaded file against the md5 in config.toml.
    Returns {filename: True | False | None}."""
    print()
    print("Initiating MD5 Checksums")

    checksum_results = {}
    for artifact in TOML_CONFIG["artifacts"]:
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