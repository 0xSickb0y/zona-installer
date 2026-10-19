# zona-installer

Linux installer for the **ZONA** modpack for S.T.A.L.K.E.R.: Anomaly, written in Python.

> This is an ongoing reimplementation of the existing
> [johnmnorman/zona-installer](https://github.com/johnmnorman/zona-installer)
> (a Bash script). It is a work in progress and not usable yet.

## Usage

Requires Python 3.11+ and 7zip.

    git clone https://github.com/0xSickb0y/zona-installer
    pip install .
    zona --help

| Command           | Status      | Description                                   |
|-------------------|-------------|-----------------------------------------------|
| `zona setup`      | in progress | Create the install and archive directories    |
| `zona install`    | planned     | Verify and install the modpack                |
| `zona uninstall`  | planned     | Remove the installed files and directories    |

## Configuration

Everything about *what* gets installed lives in __zona/config.toml__:

- install and archive directories
- the HUD and exes variants the user can choose
- every artifact: URL, filename, md5 and destination

## Development

### 1. Create the virtual environment:

> `--home`: directory on the host used as the container's __$HOME__ (pick any path).
> 
> It's created if missing, and keeps your real ~/Games untouched.

> `--volume`: the zona-installer repository folder
> 
> mounted at /src inside the container

> Add `--nvidia` if you have an NVIDIA card

```sh
distrobox create --name zona-dev \
  --image debian:bookworm \
  --home <home> \
  --volume <zona-installer-repo>:/src \
  --additional-packages "python3 python3-venv python3-pip p7zip-full"
  # --nvidia
```

### 2. Enter the virtual environment:

```sh
distrobox enter zona-dev -- bash

python3 -m venv ~/.venv
source ~/.venv/bin/activate
pip install -e /src
```

### 3. Run the installer:

```sh
zona --help
zona setup
```

## Layout

```
pyproject.toml
zona/
├── main.py          # entry point
├── config.py        # reads config.toml, defines the CLI with argparse
├── config.toml
├── utils.py         # helpers
├── setup/
│   ├── __init__.py  # run(): the steps of `zona setup`
│   ├── path_ops.py  # path operations (create, clean, etc)
│   └── download.py  # download archives
├── install/         # (empty for now)
└── uninstall/       # (empty for now)
```

## Roadmap

- [x] Config file and CLI skeleton
- [ ] Cleaning functions
- [ ] Download archives and anomaly
- [x] md5 verification
- [ ] Extract archives
- [ ] Proton / Wine / umu setup
- [ ] Launch script and `.desktop` entry
- [ ] GUI