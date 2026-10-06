import os
import requests
from zona.setup import path_ops


def download_archives(artifacts, ARCHIVES_DIR):
    """Select the artifacts, then download every file into the archives dir."""
    for artifact in artifacts:
        if artifact.get("group") == "hud":
            url = artifact["url"]
            filename = artifact["filename"]
            print(f"Fetching {url}")
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                path_ops.save_archive_to_dest(ARCHIVES_DIR, filename, response)


def select_artifacts(artifacts, hud=None, exes=None):
    """Artifacts to download: always-installed ones + the chosen hud/exes variants.
    Missing choices fall back to the defaults in [choices]."""
    pass



def resolve_url(url):
    """Return the real download URL. TODO: follow the ModDB redirect."""
    pass


def download_file(url, dest_path):
    """ODO: skip if it exists, resume, progress."""
    pass

