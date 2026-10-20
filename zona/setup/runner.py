import os
import shutil
import subprocess
from zona.setup import path_ops
from zona.core.log import logger


INSTALL_COMMANDS = {
    "apt": [
        ["sudo", "dpkg", "--add-architecture", "i386"],
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "wine", "winetricks"],
    ],
    "pacman": [
        ["sudo", "pacman", "-S", "--needed", "--noconfirm", "wine", "winetricks"],
    ],
    "dnf": [
        ["sudo", "dnf", "install", "-y", "wine", "winetricks"],
    ],
    "zypper": [
        ["sudo", "zypper", "--non-interactive", "install", "wine", "winetricks"],
    ],
}


def detect_package_manager():
    """Name of the first supported package manager found on the PATH, or None."""
    for name in INSTALL_COMMANDS:
        if shutil.which(name):
            return name
    return None


def setup_runner():
    """Make sure a runner is available. Returns True if it is."""
    print()
    if path_ops.steam_installed():
        logger.info("- [Steam found]") # TODO: decide whether to use Steam's Proton / GE-Proton / Etc
        return True
    
    logger.info("- [Steam not found]")
    if path_ops.wine_installed():
        logger.info("- [wine and winetricks already installed]")
        return True
    return install_wine()


def install_wine():
    """Install wine and winetricks with the system package manager."""
    manager = detect_package_manager()
    if manager is None:
        logger.error("- [No supported package manager found: install wine and winetricks manually]")
        return False

    logger.info(f"- [Package manager: {manager}]")
    for command in INSTALL_COMMANDS[manager]:
        logger.info(f"- [Running: {' '.join(command)}]\n")
        try:
            subprocess.run(command, check=True)
        except (subprocess.CalledProcessError, OSError) as error:
            logger.error(f"- [Command failed: {error}]\n")
            return False
    return True


def create_prefix(WINE_PREFIX_DIR):
    """Create the wine prefix with wineboot. Returns True on success."""
    if (WINE_PREFIX_DIR / "drive_c").exists():
        logger.info(f"- [Wine prefix already exists: '{WINE_PREFIX_DIR}]\n")
        return True

    # TODO: --verbose show winedebug
    env = {**os.environ, "WINEPREFIX": str(prefix_dir), "WINEDLLOVERRIDES": "mscoree,mshtml=", "WINEDEBUG": "-all"}
    logger.info(f"- [Creating wine prefix in '{WINE_PREFIX_DIR}']\n")
    try:
        result = subprocess.run(["wineboot", "-u"], env=env, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"- [Could not create the wine prefix]\n{result.stderr}")
            return False
    except (subprocess.CalledProcessError, OSError) as error:
        logger.error(f"- [Could not create the wine prefix: {error}]\n")
        return False
    return True


def install_components(WINE_PREFIX_DIR, WINE_COMPONENTS):
    """Install winetricks components into the prefix. Returns True if all succeeded."""
    env = {**os.environ, "WINEPREFIX": str(WINE_PREFIX_DIR)}
    failed = []
    for component in WINE_COMPONENTS:
        logger.info(f"- [Installing {component}]")
        try:
            # TODO: --verbose: use the line below instead to show winetricks output
            # subprocess.run(["winetricks", "-q", component], env=env, check=True)
            subprocess.run(["winetricks", "-q", component], env=env, check=True, stdout=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, OSError):
            logger.error(f"- [Failed to install {component}]")
            failed.append(component)
    if failed:
        logger.error(f"- [Failed components ({len(failed)})]")
        for component in failed:
            print(f"{'':9} - {component}")
    return not failed