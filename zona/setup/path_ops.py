import os
import shutil
from pathlib import Path
from zona.core import config
from zona.core import utils
from zona.core.log import logger

def verify_and_create_directories(INSTALL_DIR, ARCHIVES_DIR):
    zona_destinations = (INSTALL_DIR, ARCHIVES_DIR)
    verify_directories(zona_destinations)
    create_directories(zona_destinations)

def verify_directories(zona_destinations):
    """Check which directories already exist and ask whether to clean each one."""
    for path in zona_destinations:
        if not path.exists():
            continue
        question = f"Directory '{path}' already exists. Delete its contents for a fresh install? [y/N] >>> "
        if utils.yes_or_no(question, default=False):
            clean_directory(path)
        else:
            logger.info(f"[Keeping files inside '{path}']")
        print("")


def create_directories(zona_destinations):
    """Create the directories that don't exist yet."""
    for path in zona_destinations:
        if path.exists():
            continue
        path.mkdir(parents=True)
        logger.info(f"[Created directory '{path}']")


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
    logger.info(f"[Cleaned {path}]")


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

