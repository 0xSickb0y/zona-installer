import os
import shutil
from pathlib import Path
from zona.core import utils
from zona.core.log import logger


STEAM_DIRS = {
    "~/.steam/steam",
    "~/.local/share/Steam",
    "~/.var/app/com.valvesoftware.Steam",  # Flatpak
}


def verify_and_create_directories(INSTALL_DIR, ARCHIVES_DIR, WINE_PREFIX_DIR):
    """Returns (ok, results), results = {path: "cleaned" | "kept" | "created" | "failed"}."""
    zona_destinations = (INSTALL_DIR, ARCHIVES_DIR, WINE_PREFIX_DIR)
    results = verify_directories(zona_destinations)
    results.update(create_directories(zona_destinations))
    return ("failed" not in results.values(), results)


def verify_directories(zona_destinations):
    """Ask whether to clean each existing directory, skipping any nested pair in the set."""
    results = {}
    parents = list(zona_destinations)
    for path in parents:
        if not path.exists():
            continue
        if any(
            path != other and (path.is_relative_to(other) or other.is_relative_to(path))
            for other in parents
        ):
            continue  # the parent/child pair is unsafe to clean independently
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
    return any(Path(directory).expanduser().exists() for directory in STEAM_DIRS)


def wine_installed():
    """True if both wine and winetricks are on the PATH."""
    return shutil.which("wine") is not None and shutil.which("winetricks") is not None


def find_7z():
    """Path of the first 7-zip binary found on the PATH, or None."""
    for name in ("7z", "7zz", "7za"):
        path = shutil.which(name)
        if path:
            return path
    return None


def resolve_paths(toml_config, install_dir=None, archives_dir=None):
    """Directories from config.toml, with CLI values taking priority."""
    paths = {
        key: expand_var_and_user(value)
        for key, value in toml_config["defaults"].items()
    }
    if install_dir is not None:
        paths["install_dir"] = expand_var_and_user(install_dir).resolve()
        # the prefix lives inside the install dir, so it follows the override
        paths["wine_prefix_dir"] = paths["install_dir"] / "prefix"
    if archives_dir is not None:
        paths["archives_dir"] = expand_var_and_user(archives_dir).resolve()
    return paths


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