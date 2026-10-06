import os
import shutil
from zona import config
from pathlib import Path
from zona.utils import yes_or_no


def verify_and_create_directories(zona_destinations):
    for path in zona_destinations:
        try:
            path.mkdir(parents=True, exist_ok=False)
            print(f"\nCreated directory '{path}'")
        except FileExistsError:
            question = (f"Directory '{path}' already exists. Delete its contents for a fresh install? [y/N] >>> ")
            if yes_or_no(question, default=False):
                clean_directory(path)
            else:
                print(f"Keeping files inside '{path}'\n")


def expand_var_and_user(raw_path):
    expanded_path = Path(os.path.expandvars(raw_path)).expanduser()
    return expanded_path


def clean_directory(path):
    for item in path.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()
    print(f"\nCleaned {path}\n")


def save_archive_to_dest(ARCHIVES_DIR, filename, response):  
    dest_path = os.path.join(ARCHIVES_DIR, filename)
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)