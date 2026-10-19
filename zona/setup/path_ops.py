import os
import shutil
from pathlib import Path
from zona.core import config
from zona.core import utils
from zona.core.log import logger

def verify_and_create_directories(INSTALL_DIR, ARCHIVES_DIR):
    """Returns (ok, results), results = {path: "cleaned" | "kept" | "created" | "failed"}."""
    zona_destinations = (INSTALL_DIR, ARCHIVES_DIR)
    results = verify_directories(zona_destinations)
    results.update(create_directories(zona_destinations))
    return ("failed" not in results.values(), results)

def verify_directories(zona_destinations):
    """Ask whether to clean each existing directory."""
    results = {}
    for path in zona_destinations:
        if not path.exists():
            continue
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
            results[path] = "kept"
        print("")
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
    """Could be used for both download and install

    Check filename against 'ARCHIVES_DIR' for 'setup' and INSTALL_DIR  for 'install'
    """
    if ARCHIVES_DIR != None:
        path = os.path.join(ARCHIVES_DIR, filename)
        # TODO: add --verbose to log here
        return os.path.exists(path)
    elif INSTALL_DIR != None:
        path = os.path.join(INSTALL_DIR, filename)
        # TODO: add --verbose to log here
        return os.path.exists(path)


def clean_directory(path):
    for item in path.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()
    logger.info(f"- [Cleaned {path}]")


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

