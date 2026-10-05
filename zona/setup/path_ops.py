import os
import shutil
from zona import config
from pathlib import Path
from zona.utils import yes_or_no


def verify_and_create_directories(toml_defaults):
    for key in ("install_dir", "archives_dir"):
        path = Path(os.path.expandvars(toml_defaults[key])).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=False)
            print(f"Created directory '{path}'")
        except FileExistsError:
            question = (
                f"Directory '{path}' already exists. Delete its contents for a fresh install? [y/N]"
                "\n>>> "
            )
            if yes_or_no(question, default=False):
                clean_directory(path)
            else:
                print(f"Keeping files inside '{path}'")


def clean_directory(path):
    for item in path.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()
    print(f"Cleaned {path}")