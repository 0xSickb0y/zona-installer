import requests
from zona.setup import path_ops
from zona.core.log import logger


def download_archives(artifacts, ARCHIVES_DIR, hud=None, exes=None):
    """Download every missing archive.
    Returns (ok, results), results = {"Found": [...], "Downloaded": [...], "Failed": [...]}."""
    selected = select_artifacts_for_download(artifacts, ARCHIVES_DIR)
    results = {
        "Found": [item["filename"] for item in selected["Found"]],
        "Downloaded": [],
        "Failed": [],
    }
    for item in selected["Missing"]:
        try:
            download_file(item["url"], item["filename"], ARCHIVES_DIR)
            results["Downloaded"].append(item["filename"])
        except (requests.RequestException, OSError) as error:
            logger.error(f"- [Failed to fetch {item['filename']}: {error}]")
            results["Failed"].append(item["filename"])
    return (not results["Failed"], results)
 

def select_artifacts_for_download(artifacts, ARCHIVES_DIR, hud=None, exes=None):
    """
    check if "filename" already exists on the .zona_archives directory, if not download it.
    """
    SKIP_FOR_NOW = ("anomaly", "zona_modpack")  # TODO: tmp, remove when ModDB and multipart are ready
    result = {"Found": [], "Missing": []}
    for artifact in artifacts:
        if artifact["id"] in SKIP_FOR_NOW:
            continue
        for item in artifact.get("parts") or [artifact]:
            if path_ops.verify_existing_file(item["filename"], ARCHIVES_DIR=ARCHIVES_DIR):
                result["Found"].append(item)
            else:
                result["Missing"].append(item)
    return result


def download_file(url, filename, ARCHIVES_DIR):
    logger.info(f"- [Fetching {url}]")
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        path_ops.save_archive_to_dest(filename, ARCHIVES_DIR, response)



def resolve_moddb_url(url):
    """Return the real download URL. TODO: follow the ModDB redirect."""
    pass

