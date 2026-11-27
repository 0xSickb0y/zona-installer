# `zona keybinds`: open the ZONA keybind cheat sheets in the default image viewer.

import shutil
import subprocess
from pathlib import Path
from zona.core.log import logger

KEYBINDS_DIR = Path(__file__).parent.parent / "assets" / "keybinds"


def run():
    """Open every keybinds-* image (png/jpg) with the desktop's default image viewer. Returns True on success."""
    images = sorted(p for p in KEYBINDS_DIR.glob("keybinds-*") if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if not images:
        logger.error(f"- [No keybind images found in '{KEYBINDS_DIR}']")
        return False

    opener = shutil.which("xdg-open")
    if opener is None:
        logger.error("- [xdg-open not found: open the keybind images yourself:]")
        for image in images:
            print(f"{'':9} - {image}")
        return False

    for image in images:
        logger.info(f"- [Opening {image.name}]")
        try:
            # detached: the viewer keeps running after zona exits, its output is not ours to show
            subprocess.Popen(
                [opener, str(image)], start_new_session=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            logger.error(f"- [Could not open '{image}': {error}]")
            return False
    return True
