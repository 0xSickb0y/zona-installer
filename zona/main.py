from zona import setup
from zona import install
from zona.core import config
from zona.setup import path_ops
from zona.core.log import logger, setup_logging


def main():
    setup_logging()
    args = config.cli_arguments()
    version = config.get_project_version()
    paths = path_ops.resolve_paths(config.read_toml_configs(), args.install_dir, args.archives_dir)

    print(f"S.T.A.L.K.E.R.: Anomaly - ZONA modpack v{version} installer for Linux.")

    if args.command == "setup":
        logger.info("- [Initializing ZONA modpack environment setup]\n")
        setup.run(paths)

    if args.command == "install":
        logger.info("- [Initializing ZONA modpack installation]\n")
        modpack_source = setup.run(paths)  # TODO: checkpoints skip setup.run()
        install.run(paths, modpack_source)

    if args.command == "delete":
        # logger.info("- [Initializing ZONA modpack removal]\n")
        # delete.run(paths)
        pass