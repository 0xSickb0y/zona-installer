from zona import config
from zona.setup import download, hash_verification, path_ops

TOML_CONFIG = config.read_toml_configs()
ARTIFACTS = TOML_CONFIG["artifacts"]
INSTALL_DIR = path_ops.expand_var_and_user(TOML_CONFIG["defaults"]["install_dir"])
ARCHIVES_DIR = path_ops.expand_var_and_user(TOML_CONFIG["defaults"]["archives_dir"])

def run():
    path_ops.verify_and_create_directories((INSTALL_DIR, ARCHIVES_DIR))
    download.download_archives(ARTIFACTS, ARCHIVES_DIR)
    checksum_results = hash_verification.verify_archives(TOML_CONFIG, ARCHIVES_DIR)
    # TODO:
        # download archives
        # md5 checksums 
        # install wine / proton / umu
        # cleaning functions
    pass