import os
import shutil
import subprocess
from pathlib import Path
from zona.core import utils
from zona.setup import path_ops
from zona.core.log import logger


PROTONTRICKS_COMMANDS = {
    "apt": [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "protontricks"],
    ],
    "pacman": [
        ["sudo", "pacman", "-S", "--needed", "--noconfirm", "protontricks"],
    ],
    "dnf": [
        ["sudo", "dnf", "install", "-y", "protontricks"],
    ],
    "zypper": [
        ["sudo", "zypper", "--non-interactive", "install", "protontricks"],
    ],
}


SEVENZIP_COMMANDS = {
    "apt": [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "p7zip-full"],
    ],
    "pacman": [["sudo", "pacman", "-S", "--needed", "--noconfirm", "7zip"]],
    "dnf": [["sudo", "dnf", "install", "-y", "p7zip", "p7zip-plugins"]],
    "zypper": [["sudo", "zypper", "--non-interactive", "install", "7zip"]],
}


ARIA2_COMMANDS = {
    "apt": [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "aria2"],
    ],
    "pacman": [["sudo", "pacman", "-S", "--needed", "--noconfirm", "aria2"]],
    "dnf": [["sudo", "dnf", "install", "-y", "aria2"]],
    "zypper": [["sudo", "zypper", "--non-interactive", "install", "aria2"]],
}


def detect_package_manager():
    """Name of the first supported package manager found on the PATH, or None."""
    for name in PROTONTRICKS_COMMANDS:
        if shutil.which(name):
            return name
    return None


def setup_7z():
    """Make sure 7z is available, offering to install it. Returns True if it is."""
    if path_ops.find_7z():
        logger.info("- [7z found]")
        return True

    logger.warning("- [7z is not found]")
    if not utils.yes_or_no("Install 7zip now? [Y/n] >>> ", default=True):
        logger.error("- [7z is required to extract the archives]")
        return False
    return install_packages(SEVENZIP_COMMANDS, "7zip")


def setup_aria2c():
    """Make sure aria2c is available, offering to install it. Returns True if it is."""
    if path_ops.find_aria2c():
        logger.info("- [aria2c found]")
        return True

    logger.warning("- [aria2c is not found]")
    if not utils.yes_or_no("Install aria2 now? [Y/n] >>> ", default=True):
        logger.error("- [aria2c is required for magnet and torrent downloads]")
        return False
    return install_packages(ARIA2_COMMANDS, "aria2c")


def install_packages(commands_by_manager, package_label="packages"):
    """Run the install commands for the detected package manager. Returns True on success."""
    manager = detect_package_manager()
    if manager is None:
        logger.error(f"- [No supported package manager found: install {package_label} manually]")
        return False

    logger.info(f"- [Package manager: {manager}]")
    for command in commands_by_manager[manager]:
        logger.info(f"- [Running: {' '.join(command)}]")
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except OSError as error:
            logger.error(f"- [Could not run '{command[0]}': {error}]")
            return False
        if result.returncode != 0:
            logger.error(f"- [Command failed: {' '.join(command)}]")
            print(result.stderr[-1500:])
            return False
    return True


def get_proton(runners_dir):
    """Path of the GE-Proton 'proton' script, or None (with an error logged)."""
    proton = path_ops.find_ge_proton(runners_dir)
    if proton is None:
        logger.error("- [GE-Proton not found, run 'zona setup' first]")
    return proton


def proton_env(WINE_PREFIX_DIR):
    """Environment for running things in the prefix through GE-Proton.
    Proton keeps its prefix in '<compat data path>/pfx', so the compat path is the parent."""
    compat_dir = WINE_PREFIX_DIR.parent
    return {
        **os.environ,
        "STEAM_COMPAT_DATA_PATH": str(compat_dir),
        "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(compat_dir.parent),
    }


def setup_protontricks():
    """Make sure protontricks is available (it installs the prefix components). Returns True if it is."""
    if path_ops.find_protontricks():
        logger.info("- [protontricks found]")
        return True

    logger.warning("- [protontricks is not found]")
    if not utils.yes_or_no("Install protontricks now? [Y/n] >>> ", default=True):
        logger.error("- [protontricks is required to install the prefix components]")
        return False
    return install_packages(PROTONTRICKS_COMMANDS, "protontricks")


def create_prefix(WINE_PREFIX_DIR, runners_dir):
    """Create the prefix by letting GE-Proton set it up. Returns True on success."""
    if (WINE_PREFIX_DIR / "drive_c").exists():
        logger.info(f"- [Wine prefix already exists: '{WINE_PREFIX_DIR}']")
        return True

    proton = get_proton(runners_dir)
    if proton is None:
        return False

    logger.info(f"- [Creating the prefix with GE-Proton in '{WINE_PREFIX_DIR}']")
    try:
        result = subprocess.run(
            [str(proton), "run", "wineboot", "-u"],
            env=proton_env(WINE_PREFIX_DIR), capture_output=True, text=True,
        )
    except OSError as error:
        logger.error(f"- [Could not run GE-Proton: {error}]")
        return False

    if not (WINE_PREFIX_DIR / "drive_c").exists():
        logger.error(f"- [GE-Proton did not create the prefix (exit {result.returncode})]")
        print(result.stderr[-1500:])
        return False
    return True


def install_components(WINE_PREFIX_DIR, WINE_COMPONENTS, runners_dir):
    """Install Windows components into the Proton prefix without requiring a Steam AppID."""
    proton = get_proton(runners_dir)
    if proton is None:
        return False

    wine = path_ops.find_proton_wine(proton)
    if wine is None:
        logger.error("- [Could not find the Proton wine binary]")
        return False

    env = {
        **proton_env(WINE_PREFIX_DIR),
        "WINEPREFIX": str(WINE_PREFIX_DIR),
        "WINE": str(wine),
        "WINESERVER": str(wine.with_name("wineserver")),
    }

    try:
        list_result = subprocess.run(
            ["winetricks", "list-installed"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        logger.error(f"- [Could not query winetricks: {error}]")
        return False

    installed = set()
    if list_result.returncode == 0:
        output = list_result.stdout or ""
        installed = {line.strip() for line in output.splitlines() if line.strip()}

    failed = []
    print("\nInstalling Proton prefix components")
    for component in WINE_COMPONENTS:
        if component in installed:
            logger.info(f"- [Skipping already-installed component: {component}]")
            continue

        logger.info(f"- [Installing {component}]")
        try:
            result = subprocess.run(
                ["winetricks", "-q", component],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            logger.error(f"- [Could not run winetricks: {error}]")
            return False

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 0:
            installed.add(component)
            continue

        if "already installed" in output.lower() or "already exists" in output.lower():
            logger.info(f"- [Skipping already-installed component: {component}]")
            installed.add(component)
            continue

        logger.error(f"- [Failed to install {component}]")
        print(output[-1500:])
        failed.append(component)
    if failed:
        logger.error(f"- [Failed components ({len(failed)})]")
        for component in failed:
            print(f"{'':9} - {component}")
    return not failed



# def run_exe(exe_path, working_dir, WINE_PREFIX_DIR, runners_dir):
#     """Run a Windows executable through GE-Proton. Returns False only if it could not be started."""
#     proton = get_proton(runners_dir)
#     if proton is None:
#         return False

#     logger.info(f"- [Launching via GE-Proton: {exe_path.name}]")
#     try:
#         result = subprocess.run(
#             [str(proton), "run", str(exe_path)],
#             env=proton_env(WINE_PREFIX_DIR), cwd=working_dir,
#         )
#     except OSError as error:
#         logger.error(f"- [Could not run GE-Proton: {error}]")
#         return False
#     logger.info(f"- [{exe_path.name} exited with code {result.returncode}]")
#     return True

def run_exe(exe_path, working_dir, WINE_PREFIX_DIR, runners_dir):
    """Run a Windows executable through GE-Proton with the app folder as cwd."""
    proton = get_proton(runners_dir)
    if proton is None:
        return False

    exe_path = Path(exe_path)
    working_dir = Path(working_dir)

    logger.info(f"- [Launching via GE-Proton: {exe_path.name}]")
    try:
        result = subprocess.run(
            [str(proton), "run", str(exe_path)],
            env=proton_env(WINE_PREFIX_DIR),
            cwd=str(working_dir),
        )
    except OSError as error:
        logger.error(f"- [Could not run GE-Proton: {error}]")
        return False

    logger.info(f"- [{exe_path.name} exited with code {result.returncode}]")
    return True