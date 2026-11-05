import os
import shutil
import tarfile
from pathlib import Path
from zona.core import utils
from zona.core.log import logger


STEAM_ROOTS = {
    "~/.steam/steam",
    "~/.local/share/Steam",
    "~/.var/app/com.valvesoftware.Steam",  # Flatpak
}


STEAM_RUNNER_DIRS = (
    "~/.steam/root/compatibilitytools.d",
    "~/.local/share/Steam/compatibilitytools.d",
    "~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d",  # Flatpak
)

PROTECTED_STEAM_ROOTS = {
    Path("~/.steam/root").expanduser().resolve(),
    Path("~/.steam/steam/compatdata").expanduser().resolve(),
    Path("~/.local/share/Steam/compatdata").expanduser().resolve(),
    Path("~/.var/app/com.valvesoftware.Steam/data/Steam/compatdata").expanduser().resolve(),
    *{Path(root).expanduser().resolve() for root in (*STEAM_ROOTS, *STEAM_RUNNER_DIRS)},
}


def verify_and_create_directories(INSTALL_DIR, ARCHIVES_DIR, WINE_PREFIX_DIR, RUNNERS_DIR=None, artifacts=None, checksum_results=None, verify_ok=None,):
    """Returns (ok, results).

    Reuse previously verified checksum results when available.
    Otherwise, verify the archive cache before preserving it.
    """
    listed = [
        p for p in (INSTALL_DIR, ARCHIVES_DIR, WINE_PREFIX_DIR, RUNNERS_DIR)
        if p is not None
    ]

    keep_archives = False
    if ARCHIVES_DIR is not None and artifacts:
        if verify_ok is None or checksum_results is None:
            from zona.setup import hash_verification
            logger.info(f"- [Verifying archive cache at '{ARCHIVES_DIR}']")
            verify_ok, checksum_results = hash_verification.verify_archives(
                artifacts, ARCHIVES_DIR
            )
        else:
            logger.info("- [Reusing previous archive checksum verification]")
        keep_archives = verify_ok
        if keep_archives:
            logger.info("- [Archive cache verified; keeping existing files]")
        else:
            logger.warning(
                "- [Archive cache contains missing or corrupted archives]"
            )
    if keep_archives:
        listed = [p for p in listed if p != ARCHIVES_DIR]
    results = verify_directories(listed)
    if keep_archives:
        results[ARCHIVES_DIR] = "kept"
    remaining = [
        p for p in (INSTALL_DIR, ARCHIVES_DIR, WINE_PREFIX_DIR, RUNNERS_DIR)
        if p is not None and p not in results
    ]
    results.update(create_directories(remaining))
    return ("failed" not in results.values(), results)


def is_steam_managed_path(path):
    """True when the path sits under Steam's own compatdata or compatibilitytools.d trees.

    This includes both the default Steam install locations and custom Steam library paths such as
    /run/media/.../SteamLibrary/steamapps/compatdata/<appid>/pfx.
    """
    candidate = path.expanduser().resolve()
    if any(candidate == root or candidate.is_relative_to(root) for root in PROTECTED_STEAM_ROOTS):
        return True

    lower_parts = {part.lower() for part in candidate.parts}
    if "compatdata" in lower_parts or "compatibilitytools.d" in lower_parts:
        return "steamapps" in lower_parts or "steamlibrary" in lower_parts or "steam" in lower_parts
    return False


def verify_directories(zona_destinations):
    """Ask whether to clean each existing directory, while skipping nested child cleanup when the parent is already being handled.

    Steam-managed directories are protected: their compatibilitytools.d and compatdata trees are not safe to delete
    because they are owned by Steam and may contain runtime-managed data.
    """
    results = {}
    parents = list(zona_destinations)
    steam_detected = steam_installed()

    if steam_detected:
        logger.info("- [Steam found, its runners are searched too]")

    for path in parents:
        if not path.exists():
            continue

        if is_steam_managed_path(path):
            logger.info(f"- [Protected Steam-managed directory, keeping contents inside '{path}']")
            results[path] = "kept"
            continue

        nested_with_parent = any(
            path != other and path.is_relative_to(other)
            for other in parents
        )
        if nested_with_parent:
            # Keep the parent prompt, but skip the nested child when it lives under another managed target.
            continue

        print()
        question = f"Directory '{path}' already exists. Delete its contents for a fresh install? [y/N] >>> "
        if utils.yes_or_no(question, default=False):
            try:
                clean_directory(path)
                results[path] = "cleaned"
            except OSError as error:
                logger.error(f"- [Could not clean '{path}': {error}]")
                results[path] = "failed"
        else:
            logger.info(f"- [Keeping files inside '{path}']")
            print()
            results[path] = "kept"
    return results


def create_directories(zona_destinations):
    """Create the directories that don't exist yet."""
    results = {}
    for path in zona_destinations:
        if path.exists():
            continue
        try:
            path.mkdir(parents=True)
            logger.info(f"- [Created directory '{path}']")
            results[path] = "created"
        except OSError as error:
            logger.error(f"- [Could not create '{path}': {error}]")
            results[path] = "failed"
    return results


def expand_var_and_user(raw_path):
    if raw_path is None:
        return None
    if isinstance(raw_path, Path):
        raw_path = str(raw_path)
    raw_path = str(raw_path).strip()
    if raw_path == "":
        return None
    expanded_path = Path(os.path.expandvars(raw_path)).expanduser()
    return expanded_path
    

def verify_existing_file(filename, ARCHIVES_DIR=None, INSTALL_DIR=None):
    """Could be used for both download and install.

    Check filename against ARCHIVES_DIR for setup and INSTALL_DIR for install.
    """
    if ARCHIVES_DIR is not None:
        path = os.path.join(ARCHIVES_DIR, filename)
        return os.path.exists(path)
    if INSTALL_DIR is not None:
        path = os.path.join(INSTALL_DIR, filename)
        return os.path.exists(path)
    return False


def clean_directory(path):
    for item in path.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()
    logger.info(f"- [Cleaned {path}]")
    print()


def save_archive_to_dest(filename, ARCHIVES_DIR, response):
    """Stream a download to ARCHIVES_DIR/filename.

    Writes to 'filename.part' first and renames it once the download is
    complete, so an interrupted download never leaves a truncated file
    under the final name.
    """
    dest_path = os.path.join(ARCHIVES_DIR, filename)
    tmp_path = dest_path + ".part"
    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    os.replace(tmp_path, dest_path)


def steam_installed():
    """True if a native or Flatpak Steam install is found."""
    if shutil.which("steam"):
        return True
    return any(Path(directory).expanduser().exists() for directory in STEAM_ROOTS)


def find_steam_root():
    """The Steam install folder (the one that holds 'userdata'), or None."""
    for raw in STEAM_ROOTS:
        root = Path(raw).expanduser()
        if (root / "userdata").is_dir():
            return root.resolve()
    return None


def find_steam_library(prefix):
    """Find the Steam library containing the configured Proton prefix."""
    prefix = Path(prefix).expanduser().resolve()

    if prefix.name != "pfx" or prefix.parent.name != "999999":
        logger.error(f"- [Unexpected Proton prefix layout: {prefix}]")
        return None

    library = prefix.parent.parent.parent.parent

    if not (library / "steamapps").is_dir():
        logger.error(f"- [Steam library not found: {library}]")
        return None

    return library


def link_directory(link, target):
    """Make `link` a symlink to `target`. A real directory already at `link` is renamed to
    '<name>.bak' first. Returns True on success."""
    link, target = Path(link), Path(target)
    try:
        if link.is_symlink():
            if link.resolve() == target.resolve():
                return True
            link.unlink()
        elif link.exists():
            link.rename(link.with_name(link.name + ".bak"))
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        logger.error(f"- [Could not link '{link}' to '{target}': {error}]")
        return False
    logger.info(f"- [Linked '{link}' -> '{target}']")
    return True


def runner_dirs(runners_dir):
    """Folders that may hold GE-Proton: Steam's (only if Steam is installed), then ours."""
    STEAM_ROOTS = [Path(d).expanduser() for d in STEAM_RUNNER_DIRS] if steam_installed() else []
    return STEAM_ROOTS + [Path(runners_dir)]


def find_ge_proton(runners_dir, name=None):
    """Path of a GE-Proton 'proton' script, or None. With `name` (e.g. 'GE-Proton10-9')
    only that version matches, otherwise the newest one wins."""
    candidates = [
        proton
        for base in runner_dirs(runners_dir)
        for proton in base.glob(f"{name or 'GE-Proton*'}/proton")
        if proton.is_file()
    ]
    return max(candidates, key=lambda p: p.stat().st_mtime, default=None)


def find_proton_wine(proton):
    """Path to the Wine binary inside a GE-Proton install, or None."""
    if proton is None:
        return None
    proton_dir = Path(proton).resolve().parent
    candidates = (
        proton_dir / "files" / "bin" / "wine",
        proton_dir / "files" / "bin" / "wine64",
        proton_dir / "wine",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def find_protontricks():
    """Path to protontricks, or None if it is not installed."""
    return shutil.which("protontricks")


def protontricks_installed():
    """True if protontricks is on the PATH."""
    return shutil.which("protontricks") is not None


def find_7z():
    """Path of the first 7-zip binary found on the PATH, or None."""
    for name in ("7z", "7zz", "7za"):
        path = shutil.which(name)
        if path:
            return path
    return None


def find_aria2c():
    """Path to aria2c, or None if it is not installed."""
    return shutil.which("aria2c")


def steam_default_runners_dir():
    """A reasonable Steam-compatible runner location for GE-Proton lookup.

    This is used when the config does not define a custom runner directory, while still
    respecting any user-provided CLI override and the existing Steam detection logic.
    """
    for candidate in STEAM_RUNNER_DIRS:
        path = Path(candidate).expanduser()
        if path.exists():
            return path
    return Path("~/.steam/root/compatibilitytools.d").expanduser()


def steam_default_prefix_dir():
    """Base prefix path for a Steam-managed Proton prefix.

    A Proton prefix is typically under compatdata/<appid>/pfx; when the project leaves
    the default unset, use Steam's default compatdata layout rather than a hardcoded TOML path.
    """
    for root in STEAM_ROOTS:
        steam_root = Path(root).expanduser()
        if steam_root.exists():
            return (steam_root / "compatdata" / "999999" / "pfx").resolve()
    return (Path("~/.steam/steam/compatdata/999999/pfx").expanduser()).resolve()


def is_valid_steam_proton_prefix(path):
    """Best-effort validation for a Steam-style Proton prefix location.

    Accept paths that end in /compatdata/<appid>/pfx and reject obviously wrong values.
    """
    candidate = expand_var_and_user(path)
    if candidate is None:
        return False
    candidate = candidate.resolve()
    if candidate.name != "pfx":
        return False
    return "compatdata" in candidate.parts and candidate.parent.name.isdigit()


def resolve_paths(toml_config, install_dir=None, archives_dir=None, runners_dir=None, proton_prefix=None):
    """Directories from config.toml, with CLI values taking priority.

    If the default config omits the runner/prefix, we resolve a Steam-compatible default at runtime.
    This keeps the defaults flexible without hardcoding those locations into TOML.
    """
    paths = {
        key: expand_var_and_user(value)
        for key, value in toml_config["defaults"].items()
    }

    if install_dir is not None:
        paths["install_dir"] = expand_var_and_user(install_dir)
        if paths["install_dir"] is not None:
            paths["install_dir"] = paths["install_dir"].resolve()

    if archives_dir is not None:
        paths["archives_dir"] = expand_var_and_user(archives_dir)
        if paths["archives_dir"] is not None:
            paths["archives_dir"] = paths["archives_dir"].resolve()

    if proton_prefix is not None:
        paths["wine_prefix_dir"] = expand_var_and_user(proton_prefix)
        if paths["wine_prefix_dir"] is not None:
            paths["wine_prefix_dir"] = paths["wine_prefix_dir"].resolve()
            if not is_valid_steam_proton_prefix(paths["wine_prefix_dir"]):
                logger.warning(
                    "- [Custom Proton prefix does not look like a Steam compatdata/<appid>/pfx folder; continuing anyway]"
                )
    elif "wine_prefix_dir" not in paths or paths["wine_prefix_dir"] is None:
        paths["wine_prefix_dir"] = steam_default_prefix_dir()
    else:
        paths["wine_prefix_dir"] = paths["wine_prefix_dir"].resolve()

    if runners_dir is not None:
        paths["runners_dir"] = expand_var_and_user(runners_dir)
        if paths["runners_dir"] is not None:
            paths["runners_dir"] = paths["runners_dir"].resolve()
    elif "runners_dir" not in paths or paths["runners_dir"] is None:
        paths["runners_dir"] = steam_default_runners_dir()
    else:
        paths["runners_dir"] = paths["runners_dir"].resolve()

    if not paths["runners_dir"].is_absolute():
        paths["runners_dir"] = paths["runners_dir"].resolve()

    return paths


def backup_original_bin(dest):
    """Copy the original Anomaly bin folder aside before installing modded exes.

    The live bin folder must remain in place so the extracted modded EXEs can be
    merged into it and overwrite the originals while preserving every other runtime
    file in the game install.
    """
    original_bin = dest / "bin"
    backup_dir = dest / "bin (Anomaly Original)"

    if not original_bin.exists():
        return
    if backup_dir.exists():
        logger.info(f"- [Backup already exists at '{backup_dir}', keeping it]")
        return

    logger.info(f"- [Backing up original bin folder to '{backup_dir}']")
    shutil.copytree(str(original_bin), str(backup_dir), dirs_exist_ok=False)


def backup_file(path):
    """Copy path to path + '.bak' (replacing an older backup). Returns True on success."""
    try:
        shutil.copy2(path, str(path) + ".bak")
    except OSError as error:
        logger.error(f"- [Could not back up '{path}': {error}]")
        return False
    return True


def extract_tarball(tarball_path, dest_dir):
    """Extract a .tar.gz into dest_dir. Returns True on success."""
    kwargs = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
    try:
        with tarfile.open(tarball_path) as tar:
            tar.extractall(dest_dir, **kwargs)
    except (tarfile.TarError, OSError) as error:
        logger.error(f"- [Could not extract '{tarball_path.name}': {error}]")
        return False
    logger.info(f"- [Extracted {tarball_path.name} to '{dest_dir}']")
    return True


def render_template(template_path, dest_path, values):
    """Fill {{KEY}} placeholders in a template and write it to dest_path.
    Returns True on success. Line endings are preserved."""
    try:
        with open(template_path, newline="") as f:
            text = f.read()
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        with open(dest_path, "w", newline="") as f:
            f.write(text)
    except OSError as error:
        logger.error(f"- [ Could not write '{dest_path}': {error}]")
        return False
    
    logger.info(f"- [Wrote '{dest_path}']")
    return True


def remove_files(directory, filenames):
    """Delete the given files from directory. Missing files are ignored. Returns True on success."""
    for filename in filenames:
        try:
            (directory / filename).unlink(missing_ok=True)
        except OSError as error:
            logger.error(f"- [Could not delete '{filename}': {error}]")
            return False
    return True

