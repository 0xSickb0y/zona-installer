# Enables/disables mods in an MO2 profile's modlist.txt ('+Name' = enabled, '-Name' = disabled).

from pathlib import Path
from zona.core.log import logger
from zona.setup import path_ops


def set_mods_enabled(profile_dir, names, enabled):
    """Turn the named mods on or off in profile_dir/modlist.txt (backed up first).
    Order and everything else are kept, line endings included. Returns True on success;
    names that aren't in the list are reported but don't count as a failure."""
    modlist = Path(profile_dir) / "modlist.txt"
    if not modlist.is_file():
        logger.warning(f"- [No modlist.txt in '{profile_dir}', skipping]")
        return True

    try:
        with open(modlist, encoding="utf-8", newline="") as f:
            lines = f.read().splitlines(keepends=True)
    except OSError as error:
        logger.error(f"- [Could not read '{modlist}': {error}]")
        return False

    wanted, flag, changed = set(names), "+" if enabled else "-", False
    found = set()
    for i, line in enumerate(lines):
        body = line.rstrip("\r\n")
        if body[:1] in ("+", "-") and body[1:] in wanted:
            found.add(body[1:])
            if body[0] != flag:
                lines[i] = flag + line[1:]
                changed = True

    for name in sorted(wanted - found):
        logger.warning(f"- [Mod '{name}' not found in '{modlist}']")
    if not changed:
        return True

    if not path_ops.backup_file(modlist):
        return False
    try:
        with open(modlist, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
    except OSError as error:
        logger.error(f"- [Could not write '{modlist}': {error}]")
        return False
    return True
