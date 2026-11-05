import re
import subprocess
import zlib
from pathlib import Path

import vdf

from zona.core.log import logger
from zona.setup import path_ops

SHORTCUT_NAME = "S.T.A.L.K.E.R.: ZONA"  # title shown in the Steam library


def steam_running():
    """True if a Steam client is running (it would overwrite our edits when it exits)."""
    try:
        return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0
    except OSError:
        return False


def shortcut_appid(exe, name):
    """The 32-bit id Steam gives a non-Steam shortcut: crc32 of the quoted exe path + title, high bit set."""
    return zlib.crc32(f'"{exe}"{name}'.encode()) | 0x80000000


def add_shortcut(shortcuts_file, name, exe, start_dir):
    """Add the shortcut to a user's shortcuts.vdf, or refresh it if one with this name exists."""
    appid = shortcut_appid(exe, name)
    raw = shortcuts_file.read_bytes() if shortcuts_file.exists() else b""
    data = vdf.binary_loads(raw) if raw else {}
    shortcuts = data.setdefault("shortcuts", {})

    slot = next((k for k, v in shortcuts.items() if v.get("AppName", v.get("appname")) == name), None)
    if slot is None:
        slot = str(max((int(k) for k in shortcuts if k.isdigit()), default=-1) + 1)
        shortcuts[slot] = {
            "icon": "", "ShortcutPath": "", "LaunchOptions": "", "IsHidden": 0,
            "AllowDesktopConfig": 1, "AllowOverlay": 1, "OpenVR": 0, "Devkit": 0,
            "DevkitGameID": "", "DevkitOverrideAppID": 0, "LastPlayTime": 0,
            "FlatpakAppID": "", "tags": {},
        }
    # only these fields are ours; anything the user customized (tags, launch options) is kept
    shortcuts[slot].update({
        "appid": appid - 2**32, # stored as signed 32-bit int
        "appname": name,
        "exe": f'"{exe}"',
        "StartDir": f'"{start_dir}"',
    })

    shortcuts_file.parent.mkdir(parents=True, exist_ok=True)
    shortcuts_file.write_bytes(vdf.binary_dumps(data))
    return appid


def set_compat_tool(config_vdf, appid, tool):
    """Force `tool` as the compatibility tool of the shortcut in Steam's config.vdf.
    Returns False if the file has no CompatToolMapping section."""
    text = config_vdf.read_text(encoding="utf-8")
    section = re.search(r'"CompatToolMapping"\s*\{', text)
    if section is None:
        return False

    start, depth = section.end(), 1
    for end in range(start, len(text)):  # find the closing brace of the section
        depth += {"{": 1, "}": -1}.get(text[end], 0)
        if depth == 0:
            break
    block = text[start:end]

    entry = re.search(rf'"{appid}"\s*\{{[^}}]*\}}', block)
    if entry:  # already mapped: just make sure it points at our tool
        fixed = re.sub(r'("name"\s*)"[^"]*"', rf'\1"{tool}"', entry.group(0))
        block = block.replace(entry.group(0), fixed)
    else:
        block += (
            f'\t"{appid}"\n\t\t\t\t\t{{\n'
            f'\t\t\t\t\t\t"name"\t\t"{tool}"\n'
            f'\t\t\t\t\t\t"config"\t\t""\n'
            f'\t\t\t\t\t\t"priority"\t\t"250"\n'
            f'\t\t\t\t\t}}\n\t\t\t\t'
        )
    config_vdf.write_text(text[:start] + block + text[end:], encoding="utf-8")
    return True


def add_to_library(paths):
    """Add Mod Organizer 2 to Steam's library as a non-Steam game, forced to GE-Proton and
    pointed at the prefix zona installed. Returns True on success."""
    if steam_running():
        logger.error("- [Steam is running: close it completely and run this again]")
        return False

    root = path_ops.find_steam_root()
    if root is None:
        logger.error("- [Steam install not found]")
        return False

    proton = path_ops.find_ge_proton(paths["runners_dir"])
    if proton is None:
        logger.error("- [GE-Proton not found, run 'zona setup' first]")
        return False
    tool = proton.parent.name

    prefix_path = Path(paths["wine_prefix_dir"]).resolve()
    # Accept either the pfx directory itself or its parent.
    if (prefix_path / "drive_c").is_dir():
        pfx = prefix_path
    elif (prefix_path / "pfx" / "drive_c").is_dir():
        pfx = prefix_path / "pfx"
    else:
        logger.error(f"- [Could not locate Proton pfx/drive_c inside '{prefix_path}']")
        return False

    compat_data_target = pfx.parent
    mo2_dir = pfx / "drive_c" / "mo2"

    if not path_ops.verify_existing_file("ModOrganizer.exe", INSTALL_DIR=mo2_dir):
        logger.error(f"- [ModOrganizer.exe not found inside '{mo2_dir}']")
        return False
    exe = mo2_dir / "ModOrganizer.exe"

    users = sorted(p for p in (root / "userdata").iterdir() if p.name.isdigit() and p.name != "0")
    if not users:
        logger.error(f"- [No Steam user found in '{root / 'userdata'}': log in to Steam once first]")
        return False

    # Steam only offers tools that live in its compatibilitytools.d
    tools_dir = root / "compatibilitytools.d"
    if not proton.resolve().is_relative_to(tools_dir.resolve()):
        if not path_ops.link_directory(tools_dir / tool, proton.parent):
            return False

    # the shortcut itself, for every Steam account
    appid = shortcut_appid(exe, SHORTCUT_NAME)
    for user in users:
        shortcuts_file = user / "config" / "shortcuts.vdf"
        if shortcuts_file.exists():
            path_ops.backup_file(shortcuts_file)
        try:
            add_shortcut(shortcuts_file, SHORTCUT_NAME, exe, mo2_dir)
        except (OSError, SyntaxError, ValueError) as error:
            logger.error(f"- [Could not update '{shortcuts_file}': {error}]")
            return False
        logger.info(f"- [Shortcut '{SHORTCUT_NAME}' written for Steam user {user.name}]")

    # force GE-Proton for it
    config_vdf = root / "config" / "config.vdf"
    path_ops.backup_file(config_vdf)
    try:
        if set_compat_tool(config_vdf, appid, tool):
            logger.info(f"- [Compatibility tool set to {tool}]")
        else:
            logger.warning(f"- [No CompatToolMapping in config.vdf: pick {tool} in the shortcut's Properties > Compatibility]")
    except OSError as error:
        logger.error(f"- [Could not update '{config_vdf}': {error}]")
        return False

    # Let Steam use the existing ZONA prefix.
    library = path_ops.find_steam_library(pfx)

    if library is None:
        return False

    compatdata = library / "steamapps" / "compatdata"
    shortcut_compatdata = compatdata / str(appid)

    # TODO: tmp debug
    logger.info(f"- [Steam library: {library}]")
    logger.info(f"- [Shortcut compatdata: {shortcut_compatdata}]")

    # Verify the original prefix before linking.
    for folder in ("anomaly", "mo2"):
        path = pfx / "drive_c" / folder

        if not path.is_dir():
            logger.error(f"- [ZONA C:\\{folder} missing: {path}]")
            return False

    # Link the existing prefix to the shortcut's AppID.
    if pfx.parent != shortcut_compatdata:
        if not path_ops.link_directory(shortcut_compatdata, pfx.parent):
            return False

    # Verify Steam sees the existing Windows filesystem.
    steam_prefix = shortcut_compatdata / "pfx"

    for folder in ("anomaly", "mo2"):
        path = steam_prefix / "drive_c" / folder

        if path.is_dir():
            logger.info(f"- [Steam C:\\{folder} found]")
        else:
            logger.error(f"- [Steam C:\\{folder} missing: {path}]")
            return False

    logger.info("- [ZONA prefix successfully connected to Steam]")

    logger.info(f"- [Done. Start Steam: '{SHORTCUT_NAME}' is in your library]")
    return True