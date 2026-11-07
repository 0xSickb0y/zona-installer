import shutil
import tempfile
import subprocess
from pathlib import Path
from zona.setup import path_ops
from zona.core.log import logger
from zona.core.utils import yes_or_no


# def extract_archive(filename, ARCHIVES_DIR, dest):
#     """Extract ARCHIVES_DIR/filename into dest_dir. Returns True on success."""
#     seven_zip = path_ops.find_7z()
#     if seven_zip is None:
#         logger.error("- [7z not found: install 7zip (p7zip-full on Debian)]")
#         return False
#     if not path_ops.verify_existing_file(filename, ARCHIVES_DIR=ARCHIVES_DIR):
#         logger.error(f"- [Archive not found: '{ARCHIVES_DIR / filename}']")
#         return False

#     results = path_ops.create_directories((dest,))
#     if "failed" in results.values():
#         return False
    
#     logger.info(f"- [Extracting {filename} to '{dest}']")
#     try:
#         # TODO: --verbose shows output (currently not suppressed).
#         subprocess.run(
#             [seven_zip, "x", str(ARCHIVES_DIR / filename), f"-o{dest}", "-y"],
#             check=True #, stdout=subprocess.DEVNULL
#         )
#     except (subprocess.CalledProcessError, OSError) as error:
#         logger.error(f"- [Extraction failed: {error}]")
#         return False
#     return True


# def extract_artifact(artifacts, artifact_id, paths):
#     """Extract one artifact into its `dest`. Returns True on success.

#     Single archive: extract its own filename. Multipart: extract only the
#     first volume, 7z finds the other parts in the same folder.
#     """
#     artifact = next(a for a in artifacts if a["id"] == artifact_id)
#     first = artifact["parts"][0] if "parts" in artifact else artifact
#     dest = Path(artifact["dest"].format(**paths))
#     return extract_archive(first["filename"], paths["archives_dir"], dest)



import shutil
import subprocess
import tempfile
from pathlib import Path


def extract_archive(filename, ARCHIVES_DIR, dest, strip_components=0, overwrite=False):
    """Extract ARCHIVES_DIR/filename into dest_dir.

    strip_components=1 drops the archive's single top-level folder ("Bhs Hud/appdata/..." -> "appdata/...").
    Existing files are only replaced after asking, unless `overwrite` is set (the caller backed them up).
    Returns True on success.
    """
    seven_zip = path_ops.find_7z()
    if seven_zip is None:
        logger.error("- [7z not found: install 7zip (p7zip-full on Debian)]")
        return False

    archive = Path(ARCHIVES_DIR) / filename
    if not path_ops.verify_existing_file(filename, ARCHIVES_DIR=ARCHIVES_DIR):
        logger.error(f"- [Archive not found: '{archive}']")
        return False

    results = path_ops.create_directories((dest,))
    if "failed" in results.values():
        return False

    logger.info(f"- [Extracting {filename} to '{dest}']")

    try:
        if strip_components:
            if strip_components != 1:
                logger.error("- [Unsupported strip_components value, aborting]")
                raise SystemExit(1)

            with tempfile.TemporaryDirectory() as temp_dir:
                subprocess.run(
                    [seven_zip, "x", str(archive), f"-o{temp_dir}", "-y"],
                    check=True, stdout=subprocess.DEVNULL,
                )

                top_level = list(Path(temp_dir).iterdir())
                if len(top_level) != 1 or not top_level[0].is_dir():
                    logger.error("- [Unsupported archive directory structure for stripping, aborting]")
                    raise SystemExit(1)
                root = top_level[0]

                # (source, target) with the top-level folder stripped from the path
                moves = [
                    (file, Path(dest) / file.relative_to(root))
                    for file in root.rglob("*")
                    if file.is_file()
                ]

                # Check all conflicts before moving anything.
                conflicts = [target for _, target in moves if target.exists()]
                if conflicts and not overwrite:
                    print()
                    logger.warning("- [The following files already exist:]")
                    for conflict in conflicts:
                        logger.warning(f"- [{conflict}]")
                    print()
                    if not yes_or_no("Override existing files? [y/N] >>> ", default=False):
                        logger.info("- [Extraction cancelled]")
                        return False

                for source, target in moves:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(target))
        else:
            subprocess.run(
                [seven_zip, "x", str(archive), f"-o{dest}", "-y"],
                check=True,
            )

    except (subprocess.CalledProcessError, OSError) as error:
        logger.error(f"- [Extraction failed: {error}]")
        raise SystemExit(1)

    return True



def extract_artifact(artifacts, artifact_id, paths, overwrite=False):
    """Extract one artifact into its dest. Returns True on success."""
    artifact = next(a for a in artifacts if a["id"] == artifact_id)
    first = artifact["parts"][0] if "parts" in artifact else artifact

    dest = Path(artifact["dest"].format(**paths))
    strip_components = artifact.get("strip_components", 0)

    return extract_archive(
        first["filename"],
        paths["archives_dir"],
        dest,
        strip_components=strip_components,
        overwrite=overwrite,
    )
