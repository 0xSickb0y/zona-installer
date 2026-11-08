import collections
import concurrent.futures
import json
import platform
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import requests
from zona.core import progress, utils
from zona.core.log import logger
from zona.setup import hash_verification, path_ops, runner


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


def ensure_archives(artifacts, ARCHIVES_DIR, retries=1):
    """Make every archive of `artifacts` present and verified, handling each file on its own.

      1. check:    missing (or an unfinished torrent) -> fetch; present -> hash it
      2. ask once: only if some present files are corrupted (Y/n), before replacing them
      3. fetch:    each file downloads in parallel and is verified right after its own download,
                   retried `retries` times; nothing else gets hashed again

    Returns (ok, results) with results = {filename: True | False | None}.
    """
    items = [item for artifact in artifacts for item in artifact.get("parts") or [artifact]]
    results = {}

    missing = [
        i for i in items
        if not path_ops.verify_existing_file(i["filename"], ARCHIVES_DIR=ARCHIVES_DIR)
        or path_ops.is_partial_download(i["filename"], ARCHIVES_DIR)
    ]
    present = [i for i in items if i not in missing]

    if missing:
        logger.warning(f"- [Missing archives ({len(missing)})]")
        for item in missing:
            print(f"{'':9} - {item['filename']}")
            results[item["filename"]] = None

    if present:
        print("Initiating MD5 Checksums")
        _, checksum_results = hash_verification.verify_archives([{"parts": present}], ARCHIVES_DIR)
        results.update(checksum_results)
    corrupted = [i for i in present if results[i["filename"]] is not True]

    if not missing and not corrupted:
        logger.info("- [All archives verified]")
        return (True, results)

    # Files with no download source (e.g. the single modpack archive) can't be fetched; the caller decides.
    unfetchable = [i for i in missing + corrupted if not i.get("url")]
    for item in unfetchable:
        logger.warning(f"- [No download source for {item['filename']}]")

    to_fetch = [i for i in missing if i.get("url")]
    replace = [i for i in corrupted if i.get("url")]
    if replace:
        logger.error(f"- [Checksum mismatch ({len(replace)})]")
        for item in replace:
            print(f"{'':9} - {item['filename']}")
        if utils.yes_or_no(f"Replace the {len(replace)} corrupted archive(s)? [Y/n] >>> ", default=True):
            to_fetch += replace
        else:
            logger.warning("- [Keeping the corrupted archives]")

    if to_fetch:
        threads = min(8, len(to_fetch))
        logger.info(f"- [Fetching {len(to_fetch)} archive(s) ({threads} threads)]")
        # One shared progress line for every thread (download_file reuses the active tracker).
        with progress.Progress(), concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {pool.submit(fetch_and_verify, item, ARCHIVES_DIR, retries): item for item in to_fetch}
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                results.pop(item.get("previous_filename", item["filename"]), None)
                results[item["filename"]] = future.result()

    failed = [name for name, status in results.items() if status is not True]
    if failed:
        logger.error(f"- [Unusable archives ({len(failed)})]")
        for filename in failed:
            print(f"{'':9} - {filename}")
    return (not failed, results)


def fetch_and_verify(item, ARCHIVES_DIR, retries=1):
    """Download one archive and verify only that file, retrying on failure. Returns True/False/None."""
    if "primary" in item:
        # A corrupted alternative copy (e.g. the ModDB name) is replaced by the file the URL actually serves.
        path_ops.remove_files(Path(ARCHIVES_DIR), [item["filename"]])
        item["previous_filename"] = item["filename"]
        item.update(item.pop("primary"))

    status = None
    for attempt in range(retries + 1):
        try:
            # overwrite: HTTP replaces the file atomically; aria2c re-checks the torrent and only fetches bad pieces.
            download_file(item["url"], item["filename"], ARCHIVES_DIR, overwrite=True)
        except (requests.RequestException, OSError, RuntimeError, ValueError) as error:
            logger.error(f"- [Failed to fetch {item['filename']}: {error}]")
            status = None
        else:
            _, checksum_results = hash_verification.verify_archives([item], ARCHIVES_DIR)
            status = checksum_results[item["filename"]]
            if status is True:
                return True
        if attempt < retries:
            logger.warning(f"- [Retrying {item['filename']} ({attempt + 1}/{retries})]")
    return status


def download_file(url, filename, ARCHIVES_DIR, overwrite=False):
    if is_ge_proton_latest_release(url):
        resolved_name = resolve_ge_proton_filename(url, filename)
        destination = Path(ARCHIVES_DIR) / resolved_name
        if destination.exists():
            logger.info(f"- [Archive already present: '{destination}']")
            return resolved_name
        return download_latest_github_release(url, resolved_name, ARCHIVES_DIR)

    destination = Path(ARCHIVES_DIR) / filename
    if destination.exists() and not overwrite and not path_ops.is_partial_download(filename, ARCHIVES_DIR):
        logger.info(f"- [Archive already present: '{destination}']")
        return filename

    if is_torrent_source(url):
        return download_torrent(url, filename, ARCHIVES_DIR)

    print()
    logger.info(f"- [Fetching {url}]")
    with requests.get(url, stream=True, timeout=(10, 60)) as response:
        response.raise_for_status()
        stream_with_progress(filename, ARCHIVES_DIR, response)
    return filename


def stream_with_progress(filename, ARCHIVES_DIR, response):
    """Save a streamed requests response, reporting bytes to the shared progress line."""
    total = int(response.headers.get("Content-Length") or 0) or None
    with progress.tracker() as p:
        p.start(filename, total)
        path_ops.save_archive_to_dest(filename, ARCHIVES_DIR, response, on_chunk=lambda n: p.advance(filename, n))
        p.finish(filename)


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
        stream_with_progress(asset_name, ARCHIVES_DIR, response)

    return asset_name


def download_torrent(url, filename, ARCHIVES_DIR):
    """Download torrent/magnet content using aria2c when the archive source is a torrent."""
    if path_ops.find_aria2c() is None:
        if not runner.setup_aria2c():
            raise RuntimeError("aria2c is required for torrent downloads and could not be installed")

    # Note: aria2c ignores --out for BitTorrent; the file keeps the name from the torrent metadata,
    # so the artifact's filename in config.toml must match the torrent content.
    command = [
        "aria2c",
        "--allow-overwrite=true",
        "--check-integrity=true",
        "--continue=true",
        "--dht-file-path=/tmp/aria2-dht.dat",
        "--dir", str(ARCHIVES_DIR),
        "--seed-time=0",            # exit as soon as the download completes, no seeding
        "--seed-ratio=0.0",
        "--bt-stop-timeout=600",    # give up after 10 min with zero download speed
        "--summary-interval=0",     # no periodic summaries, only the 1/s readout we parse
        "--console-log-level=warn",
        "--enable-color=false",
        str(url),
    ]

    logger.info(f"- [Torrent download via aria2c: {filename}]")
    # aria2c prints one readout line per second when piped, e.g.
    #   [#6b7c3b 1.4GiB/7.8GiB(17%) CN:44 SD:3 DL:12MiB ETA:9m]
    # Parse it into the shared progress line; keep the rest to report on failure.
    tail = collections.deque(maxlen=20)
    with progress.tracker() as p:
        p.start(filename)
        # aria2c block-buffers stdout when piped; stdbuf (coreutils) makes it line-buffered.
        if shutil.which("stdbuf"):
            command = ["stdbuf", "-oL", *command]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
            for line in proc.stdout:
                match = ARIA2_READOUT.search(line)
                if match:
                    done, total = parse_size(*match.group(1, 2)), parse_size(*match.group(3, 4))
                    p.set(filename, done, total or None)
                elif line.strip():
                    tail.append(line.rstrip())
        if proc.returncode == 0:
            p.finish(filename)

    if proc.returncode != 0:
        details = "; ".join(l for l in tail if "ERR" in l or "error" in l.lower()) or f"exit code {proc.returncode}"
        raise RuntimeError(f"aria2c failed: {details}")
    if not (Path(ARCHIVES_DIR) / filename).is_file():
        raise RuntimeError(f"torrent finished but '{filename}' was not created; check the filename in config.toml")
    return filename


ARIA2_READOUT = re.compile(r"\[#\w+\s+(?:SEED\([^)]*\)\s+)?([\d.]+)([KMGT]?i?B)/([\d.]+)([KMGT]?i?B)")
SIZE_UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}


def parse_size(number, unit):
    """'1.4', 'GiB' -> bytes."""
    return int(float(number) * SIZE_UNITS.get(unit, 1))
