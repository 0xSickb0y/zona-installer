from zona import setup
from zona import config
from zona import install

def main():
    args = config.cli_arguments()
    version = config.get_project_version()

    print(f"S.T.A.L.K.E.R.: Anomaly - ZONA modpack v{version} installer for Linux.\n")

    if args.command == "setup":
        print("Initializing ZONA modpack environment setup")
        setup.run()