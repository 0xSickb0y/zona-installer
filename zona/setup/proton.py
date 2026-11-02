import requests
from zona.core.log import logger
from zona.setup import download, hash_verification, path_ops


def ensure_proton(artifacts, paths):
    """Return the 'proton' script of the latest GE-Proton, downloading and installing it
    if it is missing. Returns None if that is not possible."""
    archives_dir, runners_dir = paths["archives_dir"], paths["runners_dir"]

    ge = next(a for a in artifacts if a["id"] == "ge_proton")
    try:
        download.normalize_ge_proton_artifact_names([ge])  # asks GitHub for the latest release
    except (requests.RequestException, RuntimeError) as error:
        logger.warning(f"- [Could not check for the latest GE-Proton: {error}]")
        return path_ops.find_ge_proton(runners_dir)  # offline: use whatever is installed

    tarball = ge["parts"][0]["filename"]
    latest = tarball.removesuffix(".tar.gz")
    proton = path_ops.find_ge_proton(runners_dir, latest)
    if proton is not None:
        logger.info(f"- [{latest} found: {proton}]")
        return proton

    logger.info(f"- [{latest} not found, downloading it]")
    download_ok, _ = download.download_artifact(ge, archives_dir)
    verify_ok, _ = hash_verification.verify_archives([ge], archives_dir)
    if not (download_ok and verify_ok):
        logger.error(f"- [Could not download and verify {latest}]")
        return None
    if not path_ops.extract_tarball(archives_dir / tarball, runners_dir):
        return None
    return path_ops.find_ge_proton(runners_dir, latest)