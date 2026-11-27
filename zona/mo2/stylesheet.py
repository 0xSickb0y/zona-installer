# Installs and activates the S.T.A.L.K.E.R. Mod Organizer 2 theme (zona/assets/mo2/stylesheet).

import re
import shutil
from pathlib import Path
from zona.core.log import logger
from zona.setup import path_ops

STYLESHEET_DIR = Path(__file__).parent.parent / "assets" / "mo2" / "stylesheet"
STYLE_FILE = "stalker.qss"


def install_stylesheet(mo2_dir):
    """Copy the theme into <mo2>/stylesheets and make it MO2's active style. Returns True on success."""
    mo2_dir = Path(mo2_dir)
    target = mo2_dir / "stylesheets"
    if not target.is_dir():
        logger.error(f"- [No 'stylesheets' folder in '{mo2_dir}': is Mod Organizer 2 installed there?]")
        return False

    logger.info(f"- [Installing the MO2 stylesheet into '{target}']")
    try:
        shutil.copy2(STYLESHEET_DIR / STYLE_FILE, target / STYLE_FILE)
        # merge with MO2's own Transparent-Style/{Fallout3,Skyrim,...} instead of replacing it
        shutil.copytree(STYLESHEET_DIR / "Transparent-Style", target / "Transparent-Style", dirs_exist_ok=True)
    except OSError as error:
        logger.error(f"- [Could not copy the stylesheet: {error}]")
        return False

    return set_mo2_style(mo2_dir / "ModOrganizer.ini", STYLE_FILE)


def set_mo2_style(ini, value):
    """Set style=<value> in the [Settings] section of ModOrganizer.ini (backed up first).
    Line endings are preserved. Returns True on success."""
    ini = Path(ini)
    if not ini.is_file():
        logger.error(f"- ['{ini}' not found: run 'zona install' first]")
        return False
    if not path_ops.backup_file(ini):
        return False

    try:
        with open(ini, newline="") as f:
            text = f.read()
        eol = "\r\n" if "\r\n" in text else "\n"

        settings = re.search(r"^\[Settings\][^\r\n]*", text, re.M)  # ends before the line ending
        if settings is None:  # no section yet: add one at the end
            text = text.rstrip("\r\n") + f"{eol}{eol}[Settings]{eol}style={value}{eol}"
        else:
            next_section = re.search(r"^\[", text[settings.end():], re.M)
            end = settings.end() + next_section.start() if next_section else len(text)
            section = text[settings.end():end]
            if re.search(r"^style=.*$", section, re.M):
                section = re.sub(r"^style=[^\r\n]*", f"style={value}", section, count=1, flags=re.M)
            else:
                section = f"{eol}style={value}" + section
            text = text[:settings.end()] + section + text[end:]

        with open(ini, "w", newline="") as f:
            f.write(text)
    except OSError as error:
        logger.error(f"- [Could not update '{ini}': {error}]")
        return False

    logger.info(f"- [MO2 style set to '{value}' (old ini kept as '{ini.name}.bak')]")
    return True
