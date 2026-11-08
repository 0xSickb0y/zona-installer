import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from zona.setup import path_ops
from zona.core.log import logger
from zona.core import utils, config

DLL_OVERRIDES = config.read_toml_configs()["wine"].get("dll_overrides", "")
WINETRICKS_LIST_TIMEOUT = 120  # seconds; listing takes a few seconds on a working Wine

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


WINETRICKS_COMMANDS = {
    "apt": [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "winetricks"],
    ],
    "pacman": [["sudo", "pacman", "-S", "--needed", "--noconfirm", "winetricks"]],
    "dnf": [["sudo", "dnf", "install", "-y", "winetricks"]],
    "zypper": [["sudo", "zypper", "--non-interactive", "install", "winetricks"]],
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


def show_nix_instructions(package_label):
    """NixOS: tools are declared in configuration.nix, not installed with sudo. Print how."""
    package = NIX_PACKAGES.get(package_label, package_label)
    logger.error(f"- [NixOS detected: zona does not install packages on NixOS, add {package} yourself]")
    print(f"{'':9}   For this terminal only, then run zona again inside it:")
    print(f"{'':9}       nix-shell -p {package}")
    print(f"{'':9}   Permanently: add it to environment.systemPackages in /etc/nixos/configuration.nix:")
    print(f"{'':9}       environment.systemPackages = with pkgs; [ {package} ];")
    print(f"{'':9}   then run: sudo nixos-rebuild switch")


def setup_7z():
    """Make sure 7z is available, offering to install it. Returns True if it is."""
    if path_ops.find_7z():
        logger.info("- [7z found]")
        return True

    logger.warning("- [7z is not found]")
    if path_ops.is_nixos():  # nothing to ask: zona prints the Nix commands instead
        return install_packages(SEVENZIP_COMMANDS, "7zip")
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
    if path_ops.is_nixos():  # nothing to ask: zona prints the Nix commands instead
        return install_packages(ARIA2_COMMANDS, "aria2c")
    if not utils.yes_or_no("Install aria2 now? [Y/n] >>> ", default=True):
        logger.error("- [aria2c is required for magnet and torrent downloads]")
        return False
    return install_packages(ARIA2_COMMANDS, "aria2c")


def setup_winetricks():
    """Make sure winetricks is available, offering to install it. Returns True if it is."""
    if path_ops.find_winetricks():
        logger.info("- [winetricks found]")
        return True

    logger.warning("- [winetricks is not found]")
    if path_ops.is_nixos():  # nothing to ask: zona prints the Nix commands instead
        return install_packages(WINETRICKS_COMMANDS, "winetricks")
    if not utils.yes_or_no("Install winetricks now? [Y/n] >>> ", default=True):
        logger.error("- [winetricks is required to install the prefix components]")
        return False
    return install_packages(WINETRICKS_COMMANDS, "winetricks")


# nixpkgs attribute that provides each tool zona can install
NIX_PACKAGES = {"protontricks": "protontricks", "winetricks": "winetricks", "7zip": "p7zip", "aria2c": "aria2"}


def install_packages(commands_by_manager, package_label="packages"):
    """Run the install commands for the detected package manager. Returns True on success.
    On NixOS nothing is installed: the Nix commands to do it are printed instead."""
    if path_ops.is_nixos():
        show_nix_instructions(package_label)
        return False

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


def get_proton(paths):
    """The 'proton' script to use, or None (with an error logged).

    -r wins. Otherwise every installed Proton is considered: one is used directly, several are
    offered in a menu (newest GE-Proton first, the default). The choice is stored in
    paths["runner"], so every later step uses the same Proton without asking again.
    """
    if paths.get("runner"):
        proton = Path(paths["runner"]) / "proton"
        if not proton.is_file():
            logger.error(f"- [No 'proton' script in '{paths['runner']}': -r must point at a Proton folder]")
            return None
        return proton

    runners = path_ops.find_runners(paths["runners_dir"])
    if not runners:
        logger.error("- [No Proton found: run 'zona setup' first, or pick one with -r]")
        return None

    proton = runners[0] if len(runners) == 1 else runners[choose_runner(runners)]
    paths["runner"] = proton.parent
    logger.info(f"- [Using runner '{proton.parent.name}']")
    return proton


def choose_runner(runners):
    """Ask which Proton to use. Returns its index in `runners`."""
    steam_protons = set(path_ops.find_steam_protons())
    labels = [
        f"{proton.parent.name}  (installed by Steam)" if proton in steam_protons else proton.parent.name
        for proton in runners
    ]
    return utils.choose("runners", labels, default=0)


def proton_env(WINE_PREFIX_DIR, STEAM_ROOT, dll_overrides=False):
    """Environment for running applications through Proton.

    `dll_overrides` adds [wine].dll_overrides from config.toml. Only use it when launching programs
    (game, MO2), which is what the overrides are for; prefix creation and winetricks run without them.
    """
    pfx = Path(WINE_PREFIX_DIR).resolve()

    if pfx.name != "pfx":
        pfx = pfx / "pfx"

    env = {
        **os.environ,
        "STEAM_COMPAT_DATA_PATH": str(pfx.parent),
        "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(Path(STEAM_ROOT).resolve()),
    }
    if dll_overrides and DLL_OVERRIDES:
        env["WINEDLLOVERRIDES"] = DLL_OVERRIDES
    return env


def setup_protontricks():
    """Make sure protontricks is available (it installs the prefix components). Returns True if it is."""
    if path_ops.find_protontricks():
        logger.info("- [protontricks found]")
        return True

    logger.warning("- [protontricks is not found]")
    if path_ops.is_nixos():  # nothing to ask: zona prints the Nix commands instead
        return install_packages(PROTONTRICKS_COMMANDS, "protontricks")
    if not utils.yes_or_no("Install protontricks now? [Y/n] >>> ", default=True):
        logger.error("- [protontricks is required to install the prefix components]")
        return False
    return install_packages(PROTONTRICKS_COMMANDS, "protontricks")


def create_prefix(WINE_PREFIX_DIR, paths):
    """Create the prefix by letting Proton set it up. Returns True on success."""
    if (WINE_PREFIX_DIR / "drive_c").exists():
        logger.info(f"- [Wine prefix already exists: '{WINE_PREFIX_DIR}']")
        return True

    proton = get_proton(paths)
    if proton is None:
        return False

    logger.info(f"- [Creating the prefix with {proton.parent.name} in '{WINE_PREFIX_DIR}']")
    try:
        result = subprocess.run(
            [str(proton), "run", "wineboot", "-u"],
            env=proton_env(WINE_PREFIX_DIR, STEAM_ROOT=path_ops.find_steam_root() or Path(paths["runners_dir"]).parent),
            capture_output=True, text=True,
        )
    except OSError as error:
        logger.error(f"- [Could not run {proton.parent.name}: {error}]")
        return False

    if not (WINE_PREFIX_DIR / "drive_c").exists():
        logger.error(f"- [{proton.parent.name} did not create the prefix (exit {result.returncode})]")
        print(result.stderr[-1500:])
        return False
    return True


def install_components(WINE_PREFIX_DIR, WINE_COMPONENTS, paths):
    """Install Windows components into the Proton prefix without requiring a Steam AppID."""
    proton = get_proton(paths)
    if proton is None:
        return False

    wine = path_ops.find_proton_wine(proton)
    if wine is None:
        logger.error("- [Could not find the Proton wine binary]")
        return False

    env = {
        **proton_env(WINE_PREFIX_DIR, STEAM_ROOT=path_ops.find_steam_root() or Path(paths["runners_dir"]).parent),
        "WINEPREFIX": str(WINE_PREFIX_DIR),
        "WINE": str(wine),
        "WINESERVER": str(wine.with_name("wineserver")),
    }

    # list-installed runs first and takes seconds, so it doubles as a "does Wine start" check:
    # a broken Proton install hangs here forever otherwise. Output goes to a temp file because Wine
    # background processes inherit a pipe and keep it open, which would block even after the timeout.
    with tempfile.TemporaryFile(mode="w+") as log:
        try:
            list_result = subprocess.run(
                ["winetricks", "list-installed"],
                env=env, stdout=log, stderr=subprocess.DEVNULL, check=False,
                timeout=WINETRICKS_LIST_TIMEOUT,
            )
        except OSError as error:
            logger.error(f"- [Could not query winetricks: {error}]")
            return False
        except subprocess.TimeoutExpired:
            subprocess.run([env["WINESERVER"], "-k"], env=env, check=False)
            logger.error(
                f"- [Wine did not respond within {WINETRICKS_LIST_TIMEOUT}s: "
                f"the Proton install in '{proton.parent}' may be broken, reinstall it or pick another with -r]"
            )
            return False
        log.seek(0)
        output = log.read()

    installed = set()
    if list_result.returncode == 0:
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


def run_exe(exe_path, working_dir, WINE_PREFIX_DIR, paths, suppress_output=False):
    """Run a Windows executable through Proton with the app folder as cwd.

    `suppress_output` quiets Proton stdout/stderr when the caller doesn't want the runtime
    noise; `--verbose` can be added later without changing the function signature.
    """
    proton = get_proton(paths)
    if proton is None:
        return False

    exe_path = Path(exe_path)
    working_dir = Path(working_dir)

    logger.info(f"- [Launching via {proton.parent.name}: {exe_path.name}]")
    extra = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL} if suppress_output else {}
    try:
        result = subprocess.run(
            [str(proton), "run", str(exe_path)],
            env=proton_env(WINE_PREFIX_DIR, STEAM_ROOT=path_ops.find_steam_root() or Path(paths["runners_dir"]).parent, dll_overrides=True),
            cwd=str(working_dir),
            **extra,
        )
    except OSError as error:
        logger.error(f"- [Could not run {proton.parent.name}: {error}]")
        return False

    logger.info(f"- [{exe_path.name} exited with code {result.returncode}]")
    return True