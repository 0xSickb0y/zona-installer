import os
import hashlib
from pathlib import Path
from zona.core.log import logger


def verify_archives(artifacts, ARCHIVES_DIR):
    """Check every file against its checksum. Supports MD5 for normal artifacts and SHA512 sidecars for GE-Proton."""
    verify_ok = True
    checksum_results = {}
    for artifact in artifacts:
        for item in artifact.get("parts") or [artifact]:
            filename = item["filename"]
            file_path = os.path.join(ARCHIVES_DIR, filename)
            expected = item.get("md5")
            try:
                if filename.lower().endswith(".sha512sum"):
                    status = Path(file_path).exists()
                elif expected:
                    status = verify_md5(file_path, expected)
                else:
                    status = verify_sha512_sidecar(file_path)
            except FileNotFoundError:
                status = None
            checksum_results[filename] = status
            if not filename.lower().endswith(".sha512sum"):
                label = expected or "sha512"
                if not expected:
                    actual = read_sha512_from_sidecar(file_path)
                    label = f"sha512 {actual}" if actual else "sha512 sidecar"
                log_result(filename, label, status)
            if status is not True:
                verify_ok = False
    return (verify_ok, checksum_results)


def verify_md5(file_path, expected_md5):
    """True if the file's md5 matches the expected one (compare lowercase)."""
    return compute_digest(file_path, "md5").lower() == expected_md5.lower()


def verify_sha512_sidecar(file_path):
    """Validate a GE-Proton tarball using the checksum values stored in its .sha512sum sidecar."""
    path = Path(file_path)
    if path.name.lower().endswith(".sha512sum"):
        return path.exists()

    expected = read_sha512_from_sidecar(path)
    if expected is None:
        raise FileNotFoundError(f"No sha512 hash found for {path.name}")

    return compute_digest(path, "sha512").lower() == expected.lower()


def read_sha512_from_sidecar(file_path):
    """Return the SHA512 digest for the given archive from the matching .sha512sum sidecar."""
    path = Path(file_path)
    candidates = [
        path.with_name(f"{path.name}.sha512sum"),
        path.with_name(f"{path.name.replace('.tar.gz', '')}.sha512sum"),
    ]
    sidecar = next((candidate for candidate in candidates if candidate.exists()), None)
    if sidecar is None:
        raise FileNotFoundError(f"sha512 sidecar missing for {path.name}")

    with sidecar.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            digest, filename = parts[0], parts[-1]
            if filename in {path.name, path.name.replace('.tar.gz', '')}:
                return digest.lower()
            if line.endswith(path.name) or line.endswith(path.name.replace('.tar.gz', '')):
                return digest.lower()
    return None


def compute_digest(file_path, digest_name):
    """Return the requested digest for a file."""
    with open(file_path, "rb") as file:
        file_digest = hashlib.file_digest(file, digest_name)
    return file_digest.hexdigest()


def log_result(filename, checksum_label, status):
    """Log one checksum result."""
    if checksum_label.startswith("sha512 "):
        digest = checksum_label[7:]
        checksum_label = f"sha512 {digest[:22]:<22}..."

    if status is True:
        logger.info(f"- [{checksum_label} - {'OK':<7} - {filename}]")
    elif status is False:
        logger.error(f"- [{checksum_label} - {'FAILED':<7} - {filename}]")
    else:
        logger.warning(f"- [{checksum_label} - {'MISSING':<7} - {filename}]")