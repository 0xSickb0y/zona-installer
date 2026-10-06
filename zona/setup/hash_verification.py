import os
import hashlib


def verify_archives(TOML_CONFIG, ARCHIVES_DIR):
    """Check every downloaded file against the md5 in config.toml.
    Returns {filename: "ok" | "failed" | "missing"}."""
    print("\nInitiating MD5 Checksum")

    checksum_results = {}
    for artifact in TOML_CONFIG["artifacts"]:
        for item in artifact.get("parts") or [artifact]:
            expected_md5 = item["md5"]
            filename = item["filename"]
            file_path = os.path.join(ARCHIVES_DIR, filename)
            try:
                if verify_md5(file_path, expected_md5):
                    checksum_results[filename] = True
                    print(f"OK | {expected_md5} | {filename} ")
                else:
                    checksum_results[filename] = False
                    print(f"FAILED | {expected_md5} | {filename} ")
            except FileNotFoundError:
                checksum_results[filename] = None
                print(f"MISSING | {expected_md5} | {filename} ")
    return checksum_results


def verify_md5(file_path, expected_md5):
    """True if the file's md5 matches the expected one (compare lowercase)."""
    file_md5 = compute_md5(file_path)
    return file_md5.lower() == expected_md5.lower()


def compute_md5(file_path):
    """Return the md5 hex digest of a file. Read it in chunks: the files are large."""
    with open(file_path, "rb") as file:
        file_md5 = hashlib.file_digest(file, "md5")
    return file_md5.hexdigest()