import time
from pathlib import Path
from zona.setup import runner
from zona.core.log import logger
from zona.install import ARTIFACTS, mo2_installed, profiles_installed, modpack_installed


def run(paths):
    start = time.perf_counter()
    completed = False
    try:
        _mo2 = next(a for a in ARTIFACTS if a["id"] == "mo2")
        MO2_DIR = Path(_mo2["dest"].format(**paths))
        MO2_PATH = MO2_DIR / "ModOrganizer.exe"
        WINE_PREFIX_DIR = paths["wine_prefix_dir"]

        if not mo2_installed(MO2_DIR):
            logger.info(f"- [Mod Organizer 2 not installed in '{MO2_DIR}', aborting]")
            raise SystemExit(1)

        profiles_dir = MO2_DIR / "profiles"
        if not profiles_installed(profiles_dir):
            logger.info(f"- [ZONA profiles not installed in '{profiles_dir}', aborting]")
            raise SystemExit(1)

        if not modpack_installed(MO2_DIR):
            logger.info(f"- [ZONA modpack not installed in '{MO2_DIR}', aborting]")
            raise SystemExit(1)

        if not runner.run_exe(MO2_PATH, str(MO2_DIR), WINE_PREFIX_DIR, paths, suppress_output=True): # TODO: --verbose option removes suppress_output=True
            logger.error("- [Could not launch ModOrganizer2, aborting]")
            raise SystemExit(1)

        completed = True
    finally:
        if completed:
            duration = time.perf_counter() - start
            logger.info(f"- [zona mo2 completed in {duration:.2f}s]")