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
        logger.info(f"- [Running: {' '.join(command)}]")
        try:
            subprocess.run(command, check=True)
        except (subprocess.CalledProcessError, OSError) as error:
            logger.error(f"- [Command failed: {error}]")
            return False
    return True