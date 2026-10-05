# zona-installer

Linux installer for the **ZONA** modpack for S.T.A.L.K.E.R.: Anomaly, written in Python.

> This is an ongoing reimplementation of the existing
> [johnmnorman/zona-installer](https://github.com/johnmnorman/zona-installer)
> (a Bash script). It is a work in progress and not usable yet.

## Usage

Requires Python 3.11+.

    pip install -e .
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

- [ ] Config file and CLI skeleton
- [ ] Cleaning functions
- [ ] Download archives and anomaly
- [ ] md5 verification
- [ ] Extract archives
- [ ] Proton / Wine / umu setup
- [ ] Launch script and `.desktop` entry
- [ ] GUI
