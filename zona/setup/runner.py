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


SEVENZIP_COMMANDS = {
    "apt": [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "p7zip-full"],
    ],
    "pacman": [["sudo", "pacman", "-S", "--needed", "--noconfirm", "7zip"]],
    "dnf": [["sudo", "dnf", "install", "-y", "p7zip", "p7zip-plugins"]],
    "zypper": [["sudo", "zypper", "--non-interactive", "install", "7zip"]],
}


def detect_package_manager():
    """Name of the first supported package manager found on the PATH, or None."""
    for name in INSTALL_COMMANDS:
        if shutil.which(name):
            return name
    return None


def setup_7z():
    """Make sure 7z is available, offering to install it. Returns True if it is."""
    if path_ops.find_7z():
        logger.info("- [7z found]")
        return True

    logger.warning("- [7z is not found]")
    if not utils.yes_or_no("Install zip now? [Y/n] >>> ", default=True):
        logger.error("- [7z is required to extract the archives]")
        return False
    return install_packages(SEVENZIP_COMMANDS)


def install_packages(commands_by_manager):
    """Run the install commands for the detected package manager. Returns True on success."""
    manager = detect_package_manager()
    if manager is None:
        logger.error("- [No supported package manager found: install 7zip manually]")
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
    env = {**os.environ, "WINEPREFIX": str(WINE_PREFIX_DIR), "WINEDLLOVERRIDES": "mscoree,mshtml=", "WINEDEBUG": "-all"}
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
            subprocess.run(["winetricks", "-q", component], env=env, check=True, stdout=subprocess.DEVNULL) # still not supressing output (why?)
        except (subprocess.CalledProcessError, OSError):
            logger.error(f"- [Failed to install {component}]")
            failed.append(component)
    if failed:
        logger.error(f"- [Failed components ({len(failed)})]")
        for component in failed:
            print(f"{'':9} - {component}")
    return not failed


def run_exe(exe_path, working_dir, WINE_PREFIX_DIR):
    """(TMP for DEMO) Run a Windows executable with wine inside the prefix. Returns False if wine can't run."""
    env = {**os.environ, "WINEPREFIX": str(WINE_PREFIX_DIR)}
    logger.info(f"- [Launching {exe_path.name}]")
    try:
        result = subprocess.run(["wine", str(exe_path)], env=env, cwd=working_dir)
    except OSError as error:
        logger.error(f"- [Could not run wine: {error}]")
        return False
    logger.info(f"- [{exe_path.name} exited with code {result.returncode}]")
    return True