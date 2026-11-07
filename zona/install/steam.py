import re
import vdf
import zlib
import subprocess
from pathlib import Path
from zona.core import utils
from zona.core.log import logger
from zona.install import ARTIFACTS
from zona.setup import path_ops, runner



SHORTCUT_NAME = "S.T.A.L.K.E.R.: ZONA"  # title shown in the Steam library
FLATPAK_APP_ID = "com.valvesoftware.Steam"


def steam_running():
    """True if a Steam client is running (it would overwrite our edits when it exits)."""
    try:
        return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0
    except OSError:
        return False


def shortcut_appid(exe, name):
    """The 32-bit id Steam gives a non-Steam shortcut: crc32 of the quoted exe path + title, high bit set."""
    return zlib.crc32(f'"{exe}"{name}'.encode()) | 0x80000000


def add_shortcut(shortcuts_file, name, exe, start_dir, launch_options):
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
        "LaunchOptions": launch_options,
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

    mo2 = next(a for a in ARTIFACTS if a["id"] == "mo2")
    anomaly = next(a for a in ARTIFACTS if a["id"] == "anomaly")
    mo2_dir = Path(mo2["dest"].format(**paths))
    anomaly_dir = Path(anomaly["dest"].format(**paths))

    if not path_ops.verify_existing_file("ModOrganizer.exe", INSTALL_DIR=mo2_dir):
        logger.error(f"- [ModOrganizer.exe not found inside '{mo2_dir}']")
        return False
    exe = mo2_dir / "ModOrganizer.exe"

    users = sorted(p for p in (root / "userdata").iterdir() if p.name.isdigit() and p.name != "0")
    if not users:
        logger.error(f"- [No Steam user found in '{root / 'userdata'}': log in to Steam once first]")
        return False

    # Flatpak Steam is sandboxed: it must be allowed to see the install folder and GE-Proton
    # (zona links GE-Proton into compatibilitytools.d; the link target must be visible too).
    if path_ops.is_flatpak_steam(root):
        logger.info("- [Flatpak Steam detected]")
        if not ensure_flatpak_access([Path(paths["install_dir"]), proton.parent.resolve()]):
            return False

    # Steam only offers tools that live in its compatibilitytools.d
    tools_dir = root / "compatibilitytools.d"
    if not proton.resolve().is_relative_to(tools_dir.resolve()):
        if not path_ops.link_directory(tools_dir / tool, proton.parent):
            return False

    # the shortcut itself, for every Steam account
    appid = shortcut_appid(exe, SHORTCUT_NAME)
    launch_options = f'WINEDLLOVERRIDES="{runner.DLL_OVERRIDES}" %command%' if runner.DLL_OVERRIDES else ""
    for user in users:
        shortcuts_file = user / "config" / "shortcuts.vdf"
        if shortcuts_file.exists():
            path_ops.backup_file(shortcuts_file)
        try:
            add_shortcut(shortcuts_file, SHORTCUT_NAME, exe, mo2_dir, launch_options)
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

    # Verify the Anomaly folder.
    if not anomaly_dir.is_dir():
        logger.error(f"- [Anomaly folder missing: {anomaly_dir}]")
        return False

    logger.info("- [ZONA prefix successfully connected to Steam]")
    logger.info(f"- [Done. Start Steam: '{SHORTCUT_NAME}' is in your library]")
    return True


def flatpak_filesystems():
    """The filesystem permissions of Flatpak Steam: its own plus the user's overrides."""
    tokens = []
    for command in (
        ["flatpak", "info", "--show-permissions", FLATPAK_APP_ID],
        ["flatpak", "override", "--user", "--show", FLATPAK_APP_ID],
    ):
        try:
            output = subprocess.run(command, capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            continue
        for line in output.splitlines():
            if line.startswith("filesystems="):
                tokens += [t for t in line.split("=", 1)[1].split(";") if t]
    return tokens


def flatpak_can_write(path, tokens):
    """True if Flatpak Steam can read and write `path` (its own data dir, 'home', 'host' or a parent folder)."""
    path = Path(path).resolve()
    if path.is_relative_to(Path(path_ops.FLATPAK_STEAM_APP_DIR).expanduser().resolve()):
        return True
    for token in tokens:
        name, _, mode = token.partition(":")
        if name.startswith("!") or mode == "ro":
            continue
        if name == "host":
            return True
        if name == "home" and path.is_relative_to(Path.home().resolve()):
            return True
        if name.startswith(("/", "~")) and path.is_relative_to(Path(name).expanduser().resolve()):
            return True
    return False


def ensure_flatpak_access(folders):
    """Make sure Flatpak Steam can use `folders`; offer to grant access if not. Returns True if it can."""
    tokens = flatpak_filesystems()
    missing = [folder for folder in folders if not flatpak_can_write(folder, tokens)]
    if not missing:
        return True

    logger.warning("- [Flatpak Steam cannot access these folders (it runs sandboxed):]")
    for folder in missing:
        print(f"{'':9} - {folder}")
    commands = [["flatpak", "override", "--user", f"--filesystem={folder}", FLATPAK_APP_ID] for folder in missing]
    if not utils.yes_or_no("Grant Flatpak Steam access to them? [Y/n] >>> ", default=True):
        logger.error("- [Without access Steam cannot start ZONA. To grant it later, run:]")
        for command in commands:
            print(f"{'':9}   {' '.join(command)}")
        return False

    for command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as error:
            logger.error(f"- [Could not run '{' '.join(command)}': {error}]")
            return False
        logger.info(f"- [Granted Flatpak Steam access to '{command[3].split('=', 1)[1]}']")
    return True


def find_library(path):
    """The Steam library folder that contains `path`, or None.
    Valid means: listed in Steam's libraryfolders.vdf and has a 'steamapps' folder."""
    root = path_ops.find_steam_root()
    if root is None:
        logger.error("- [Steam install not found]")
        return None

    vdf_file = root / "steamapps" / "libraryfolders.vdf"
    try:
        folders = vdf.loads(vdf_file.read_text(encoding="utf-8"))["libraryfolders"]
    except (OSError, SyntaxError, KeyError) as error:
        logger.error(f"- [Could not read '{vdf_file}': {error}]")
        return None

    path = Path(path).resolve()
    for folder in folders.values():
        if not isinstance(folder, dict) or "path" not in folder:
            continue
        library = Path(folder["path"]).resolve()
        if path.is_relative_to(library) and (library / "steamapps").is_dir():
            return library
    return None


def shortcut_prefix(paths):
    """The prefix Steam will use for the ZONA shortcut, or None:
    <Steam root>/steamapps/compatdata/<appid>/pfx"""
    root = path_ops.find_steam_root()
    if root is None:
        logger.error("- [Steam install not found]")
        return None
    mo2 = next(a for a in ARTIFACTS if a["id"] == "mo2")
    exe = Path(mo2["dest"].format(**paths)) / "ModOrganizer.exe"
    appid = shortcut_appid(exe, SHORTCUT_NAME)
    return root / "steamapps" / "compatdata" / str(appid) / "pfx"