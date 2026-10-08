from zona import setup
from zona.core import config
from zona.core.log import logger, setup_logging

def main():
    setup_logging()
    args = config.cli_arguments()
    version = config.get_project_version()

    print(f"S.T.A.L.K.E.R.: Anomaly - ZONA modpack v{version} installer for Linux.")

    if args.command == "setup":
        logger.info("[Initializing ZONA modpack environment setup]\n")
        setup.run()