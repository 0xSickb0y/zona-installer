import requests
from zona.setup import path_ops
from zona.core.log import logger


def download_archives(artifacts, ARCHIVES_DIR, hud=None, exes=None):
    """Select the artifacts, then download every file into the archives dir."""
    result = select_artifacts_for_download(artifacts, ARCHIVES_DIR)
    # TODO: add --verbose log here (Found, Missing)
    for item in result["Missing"]:
        url = item["url"]
        filename = item["filename"]
        download_file(url, filename, ARCHIVES_DIR)
 

def select_artifacts_for_download(artifacts, ARCHIVES_DIR, hud=None, exes=None): # TODO: implement hud from default(bhs) and CLI flags --hud clean or --hud bhs
    """
    check if "filename" already exists on the .zona_archives directory, if not download it.
    """
    result = {"Found": [], "Missing": []}
    for artifact in artifacts:
        if artifact.get("group") != "hud":
            continue
        for item in artifact.get("parts") or [artifact]:
            if path_ops.verify_existing_file(item["filename"], ARCHIVES_DIR=ARCHIVES_DIR):
                result["Found"].append(item)
            else:
                result["Missing"].append(item)
    return result


def download_file(url, filename, ARCHIVES_DIR):
    logger.info(f"[Fetching {url}]")
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        path_ops.save_archive_to_dest(filename, ARCHIVES_DIR, response)



def resolve_moddb_url(url):
    """Return the real download URL. TODO: follow the ModDB redirect."""
    pass

