import json
import platform
import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import requests
from zona.core.log import logger
from zona.setup import path_ops, runner


def is_torrent_source(url):
    """Return True for magnet links and .torrent URLs."""
    parsed = urlparse(url)
    return url.startswith("magnet:") or parsed.path.lower().endswith(".torrent")


def is_ge_proton_latest_release(url):
    """Return True only for the GE-Proton latest-release API endpoint."""
    return "api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest" in url


def resolve_ge_proton_filename(url, preferred_filename=""):
    """Return the actual latest GE-Proton archive filename for the given release URL."""
    if not is_ge_proton_latest_release(url):
        return preferred_filename

    assets = resolve_ge_proton_assets(url)
    if preferred_filename:
        lower_name = preferred_filename.lower()
        if lower_name.endswith(".sha512sum"):
            return assets["sidecar_name"]
        if lower_name.endswith(".tar.gz"):
            return assets["tarball_name"]
    return assets["tarball_name"]


def normalize_ge_proton_artifact_names(artifacts):
    """Rewrite GE-Proton entries to the exact latest release filenames from GitHub without repeating lookups."""
    for artifact in artifacts:
        entries = artifact.get("parts") or [artifact]
        ge_items = [item for item in entries if item.get("url") and is_ge_proton_latest_release(item.get("url"))]
        if not ge_items:
            continue

        resolved_by_url = {}
        for position, item in enumerate(ge_items):
            url = item.get("url")
            if not url or not is_ge_proton_latest_release(url):
                continue
            if url not in resolved_by_url:
                resolved_by_url[url] = resolve_ge_proton_assets(url)
            asset = resolved_by_url[url]

            if position % 2 == 1:
                item["filename"] = asset["sidecar_name"]
            else:
                item["filename"] = asset["tarball_name"]

        if len(ge_items) == 1:
            url = ge_items[0]["url"]
            asset = resolved_by_url[url]
            sidecar_item = {"url": url, "filename": asset["sidecar_name"]}
            if artifact.get("parts") is None:
                artifact["parts"] = [
                    {"url": url, "filename": asset["tarball_name"]},
                    sidecar_item,
                ]
                if "filename" in artifact:
                    del artifact["filename"]


def download_archives(artifacts, ARCHIVES_DIR):
    """Download every missing archive.
    Returns (ok, results), results = {"Found": [...], "Downloaded": [...], "Failed": [...]}."""
    normalize_ge_proton_artifact_names(artifacts)
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
        except (requests.RequestException, OSError, RuntimeError, ValueError) as error:
            logger.error(f"- [Failed to fetch {item['filename']}: {error}]")
            results["Failed"].append(item["filename"])
    return (not results["Failed"], results)


def download_artifact(artifact, ARCHIVES_DIR):
    """Download the missing files of one artifact (single file or multipart).
    Returns (ok, failed_filenames)."""
    failed = []
    for item in artifact.get("parts") or [artifact]:
        if path_ops.verify_existing_file(item["filename"], ARCHIVES_DIR=ARCHIVES_DIR):
            continue
        try:
            download_file(item["url"], item["filename"], ARCHIVES_DIR)
        except (requests.RequestException, OSError, RuntimeError, ValueError) as error:
            logger.error(f"- [Failed to fetch {item['filename']}: {error}]")
            failed.append(item["filename"])
    return (not failed, failed)


def select_artifacts_for_download(artifacts, ARCHIVES_DIR):
    """
    check if "filename" already exists on the .zona_archives directory, if not download it.
    """
    result = {"Found": [], "Missing": []}
    for artifact in artifacts:
        if "one_of" in artifact:
            continue  # one_of artifacts are handled by modpack.ensure_modpack()
        for item in artifact.get("parts") or [artifact]:
            if path_ops.verify_existing_file(item["filename"], ARCHIVES_DIR=ARCHIVES_DIR):
                result["Found"].append(item)
            else:
                result["Missing"].append(item)
    return result


def download_file(url, filename, ARCHIVES_DIR):
    if is_ge_proton_latest_release(url):
        resolved_name = resolve_ge_proton_filename(url, filename)
        destination = Path(ARCHIVES_DIR) / resolved_name
        if destination.exists():
            logger.info(f"- [Archive already present: '{destination}']")
            return resolved_name
        return download_latest_github_release(url, resolved_name, ARCHIVES_DIR)

    destination = Path(ARCHIVES_DIR) / filename
    if destination.exists():
        logger.info(f"- [Archive already present: '{destination}']")
        return filename

    if is_torrent_source(url):
        return download_torrent(url, filename, ARCHIVES_DIR)

    logger.info(f"- [Fetching {url}]")
    with requests.get(url, stream=True, timeout=(10, 60)) as response:
        response.raise_for_status()
        path_ops.save_archive_to_dest(filename, ARCHIVES_DIR, response)


@lru_cache(maxsize=None)
def resolve_ge_proton_assets(api_url):
    """Return the latest GE-Proton tarball and .sha512sum metadata for the current upstream release."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "zona-installer"}
    with requests.get(api_url, headers=headers, timeout=(10, 60)) as response:
        response.raise_for_status()
        payload = response.json()

    assets = payload.get("assets", [])
    if not assets:
        raise RuntimeError(f"No assets found in release metadata for {api_url}")

    machine = platform.machine().lower()
    arch_tags = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    target_arch = arch_tags.get(machine, machine)

    tarball = next(
        (
            asset for asset in assets
            if "GE-Proton" in asset.get("name", "")
            and asset.get("name", "").endswith(".tar.gz")
            and target_arch in asset.get("name", "").lower()
        ),
        None,
    )
    if tarball is None:
        tarball = next(
            (
                asset for asset in assets
                if "GE-Proton" in asset.get("name", "")
                and asset.get("name", "").endswith(".tar.gz")
            ),
            None,
        )

    sidecar = next(
        (
            asset for asset in assets
            if "GE-Proton" in asset.get("name", "")
            and asset.get("name", "").endswith(".sha512sum")
            and target_arch in asset.get("name", "").lower()
        ),
        None,
    )
    if sidecar is None:
        sidecar = next(
            (
                asset for asset in assets
                if "GE-Proton" in asset.get("name", "")
                and asset.get("name", "").endswith(".sha512sum")
            ),
            None,
        )

    if tarball is None or sidecar is None:
        raise RuntimeError(f"Could not find the GE-Proton tarball and sha512 sidecar in {api_url}")

    return {
        "tarball_url": tarball["browser_download_url"],
        "tarball_name": tarball["name"],
        "sidecar_url": sidecar["browser_download_url"],
        "sidecar_name": sidecar["name"],
    }


def download_latest_github_release(api_url, filename, ARCHIVES_DIR):
    """Resolve the latest GitHub release asset and download the matching GE-Proton archive or sidecar."""
    assets = resolve_ge_proton_assets(api_url)
    lower_name = filename.lower()

    if lower_name.endswith(".sha512sum"):
        asset_url = assets["sidecar_url"]
        asset_name = assets["sidecar_name"]
    else:
        asset_url = assets["tarball_url"]
        asset_name = assets["tarball_name"]

    logger.info(f"- [Downloading GE-Proton asset: {asset_name}]")
    with requests.get(asset_url, stream=True, timeout=(10, 60), headers={"User-Agent": "zona-installer"}) as response:
        response.raise_for_status()
        path_ops.save_archive_to_dest(asset_name, ARCHIVES_DIR, response)

    return asset_name


def download_torrent(url, filename, ARCHIVES_DIR):
    """Download torrent/magnet content using aria2c when the archive source is a torrent."""
    if path_ops.find_aria2c() is None:
        if not runner.setup_aria2c():
            raise RuntimeError("aria2c is required for torrent downloads and could not be installed")

    command = [
        "aria2c",
        "--allow-overwrite=true",
        "--check-integrity=true",
        "--continue=true",
        "--dht-file-path=/tmp/aria2-dht.dat",
        "--dir", str(ARCHIVES_DIR),
        "--out", filename,
        "--seed-time=0",
        str(url),
    ]

    logger.info(f"- [Torrent download via aria2c: {url}]")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "aria2c failed")
