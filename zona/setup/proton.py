import requests
from zona.core.log import logger
from zona.download import download
from zona.setup import hash_verification, path_ops, runner


def ensure_proton(artifacts, paths):
    """Return the 'proton' script to use, downloading the latest GE-Proton only if no Proton
    is installed at all. Returns None if that is not possible.

    -r, or a single installed Proton, is used directly; several installed Protons are offered
    in a menu (see runner.get_proton). The choice is stored in paths["runner"].
    """
    if paths.get("runner") or path_ops.find_runners(paths["runners_dir"]):
        return runner.get_proton(paths)

    logger.info("- [No Proton found, downloading GE-Proton]")
    proton = download_latest_ge_proton(artifacts, paths)
    if proton is not None:
        paths["runner"] = proton.parent
    return proton


def download_latest_ge_proton(artifacts, paths):
    """Download, verify and extract the latest GE-Proton into the runners folder (-s).
    Returns its 'proton' script, or None."""
    archives_dir, runners_dir = paths["archives_dir"], paths["runners_dir"]

    ge = next(a for a in artifacts if a["id"] == "ge_proton")
    try:
        download.normalize_ge_proton_artifact_names([ge])  # asks GitHub for the latest release
    except (requests.RequestException, RuntimeError) as error:
        logger.error(f"- [Could not check for the latest GE-Proton: {error}]")
        return None

    tarball = ge["parts"][0]["filename"]
    latest = tarball.removesuffix(".tar.gz")
    download_ok, _ = download.download_artifact(ge, archives_dir)
    verify_ok, _ = hash_verification.verify_archives([ge], archives_dir)
    if not (download_ok and verify_ok):
        logger.error(f"- [Could not download and verify {latest}]")
        return None
    if not path_ops.extract_tarball(archives_dir / tarball, runners_dir):
        return None
    return path_ops.find_ge_proton(runners_dir, latest)
