import shutil
import subprocess
from zona.setup import path_ops
from zona.core.log import logger



def extract_archive(filename, ARCHIVES_DIR, dest):
    """Extract ARCHIVES_DIR/filename into dest_dir. Returns True on success."""
    seven_zip = path_ops.find_7z()
    if seven_zip is None:
        logger.error("- [7z not found: install 7zip (p7zip-full on Debian)]")
        return False
    if not path_ops.verify_existing_file(filename, ARCHIVES_DIR=ARCHIVES_DIR):
        logger.error(f"- [Archive not found: '{ARCHIVES_DIR / filename}']")
        return False

    results = path_ops.create_directories((dest,))
    if "failed" in results.values():
        return False
    
    logger.info(f"- [Extracting {filename} to '{dest}']")
    try:
        # TODO: --verbose
        subprocess.run(
            [seven_zip, "x", str(ARCHIVES_DIR / filename), f"-o{dest}", "-y"],
            check=True, stdout=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, OSError) as error:
        logger.error(f"- [Extraction failed: {error}]")
        return False
    return True
