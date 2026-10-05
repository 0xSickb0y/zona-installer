from zona import config
from zona.setup import download, path_ops

print("Loading configuration from 'config.toml'")
TOML_DEFAULTS = config.read_toml_configs()["defaults"]

def run():
    path_ops.verify_and_create_directories(TOML_DEFAULTS)
    # TODO:
        # download archives
        # md5 checksums 
        # install wine / proton / umu
        # cleaning functions
    pass