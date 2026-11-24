# zona-installer

Linux installer for the **ZONA** modpack for S.T.A.L.K.E.R.: Anomaly, written in Python.

> This is an ongoing reimplementation of the existing
> [johnmnorman/zona-installer](https://github.com/johnmnorman/zona-installer)
> (a Bash script). It is a work in progress.

## Requirements

- Python 3.11+
- The following tools are needed at runtime. If one is missing, the installer
  offers to install it with your package manager (apt, pacman, dnf or zypper):
  - `7z` (7zip / p7zip) to extract the archives
  - `aria2c` to download Anomaly from its magnet link
  - `winetricks` and `protontricks` to install the prefix components
- **Steam** (currently a hard requirement). GE-Proton runs through Steam's
  runtime and compatdata layout, so Steam must be installed even if you don't
  use the Steam integration. Support for [umu-launcher](https://github.com/Open-Wine-Components/umu-launcher)
  is planned and will remove this requirement.
- GE-Proton. The latest release is downloaded automatically if none is found.

## Usage

### 1. Get the installer

```sh
git clone https://github.com/0xSickb0y/zona-installer
cd zona-installer
```

### 2. Create a virtual environment (optional)

```sh
python3 -m venv .venv
```

Then activate it with the line for your shell:

| Shell        | Command                          |
|--------------|----------------------------------|
| bash / zsh   | `source .venv/bin/activate`      |
| fish         | `source .venv/bin/activate.fish` |
| csh / tcsh   | `source .venv/bin/activate.csh`  |

Run the activation again in every new terminal before using `zona`.

### 3. Install and run

```sh
pip install .
zona --help
```

To work on the installer itself, use `pip install -e .` instead, so `zona` runs your edited files directly.

> ⚠️ **Already have the archives?** You don't have to torrent or re-download anything. Drop the files into the
> archives folder (`~/Games/.zona_archives` by default, or the folder you pass with `-a`) and run `zona install`
> as usual. zona checks what is already there, verifies each file's MD5 and only downloads what is missing or
> corrupted. The file names must match exactly:
>
> | Archive | File name(s) |
> |---|---|
> | Anomaly 1.5.3 | `Anomaly-1.5.3-Full.7z` (torrent) **or** `Anomaly-1.5.3-Full.2.7z` (ModDB) |
> | Modded exes | `STALKER-Anomaly-modded-exes_2026.9.12.zip` |
> | Mod Organizer 2 | `Mod.Organizer-2.5.2.7z` |
> | ZONA profiles | `zona_profiles.7z` |
> | ZONA modpack | `Zona v1.38.7z` **or** all of `zona_multipart.7z.001` … `.007` |
> | HUD | `bhs_hud.7z` and/or `clean_hud.7z` |
>
> A file with the right name but a wrong MD5 is treated as corrupted, and zona offers to replace it.
> GE-Proton is not needed in this folder: any Proton already installed is used (see `-r`).

### Commands

| Command         | Status      | Description                                                                 |
|-----------------|-------------|-----------------------------------------------------------------------------|
| `zona download` | working     | Download the archives and verify their checksums, without touching the prefix |
| `zona setup`    | working     | Download/verify the archives, create the directories, set up GE-Proton and the prefix |
| `zona install`  | working     | Run `setup`, then extract Anomaly, the modded exes, HUD, MO2, profiles and the modpack, and write the MO2 INIs |
| `zona mo2`      | working     | Launch Mod Organizer 2 through GE-Proton                                    |
| `zona steam`    | working     | Add MO2 to the Steam library as a non-Steam game (forced to GE-Proton)      |
| `zona stylesheet` | working   | Install and activate the S.T.A.L.K.E.R. theme in an existing MO2           |
| `zona keybinds` | working     | Open the ZONA keybind pictures in the default image viewer                  |
| `zona delete`   | planned     | Remove the installed files and directories                                  |

### Options

| Flag                       | Commands                              | Description                                         |
|----------------------------|---------------------------------------|-----------------------------------------------------|
| `-b`, `--no-banner`        | all (before the command)              | Hide the startup banner                             |
| `-i`, `--install-dir DIR`  | setup, install, delete, mo2, steam, stylesheet | Where ZONA is installed (default `~/Games/ZONA`)    |
| `-a`, `--archives-dir DIR` | download, setup, install, delete      | Where archives are stored (default `~/Games/.zona_archives`) |
| `-s`, `--steam-runners DIR`| setup, install, delete, mo2, steam    | Where GE-Proton is looked up / stored (default: Steam's `compatibilitytools.d`) |
| `-r`, `--runner DIR`       | setup, install, delete, mo2, steam    | Use this Proton instead of GE-Proton, e.g. `~/.steam/steam/steamapps/common/Proton - Experimental` |
| `-p`, `--proton-prefix DIR`| setup, install, delete, mo2           | Proton prefix to use (default: `<steam>/compatdata/999999/pfx`; not with `--steam`) |
| `--steam`                  | install                               | Also add MO2 to the Steam library                   |
| `--mo2-stylesheet`         | install                               | Also install and activate the S.T.A.L.K.E.R. MO2 theme |
| `--clean-hud`              | install                               | Install the clean HUD (default)                     |
| `--bhs-hud`                | install                               | Install the BHS HUD; disables the Medik health monitor mods in the SSS23.5 profile |

### HUD

ZONA comes with two HUDs. Pick one at install time; the **clean HUD is the default**.

```sh
zona install              # clean HUD
zona install --bhs-hud    # BHS HUD
```

> **Note**
> - The clean HUD is meant for the `ZONA V1.38 SSS23.5 (High Graphics)` profile; select that profile in MO2.
> - `--bhs-hud` also **disables** two mods in the SSS23.5 profile:
>   `New v1.38 Medik Health Monitor by sulikz Jeremussy Adapted by Drako` (priority 344) and
>   `New v1.38 Medik Health Monitor Presetting` (priority 357). Other profiles are not touched.
> - You can switch later: re-run `zona install` with the other flag. Choosing the clean HUD turns those two
>   mods back on. `modlist.txt` is backed up as `modlist.txt.bak` before each change.
> - Both HUDs replace Anomaly's `appdata/user.ltx` and `gamedata/configs/axr_options.ltx`. The originals are
>   kept once as `user.ltx.bak` and `axr_options.ltx.bak`.

### Steam integration

`zona install --steam` (or `zona steam` after an install) adds Mod Organizer 2 to
Steam as a non-Steam game, forces GE-Proton as its compatibility tool and uses the
prefix Steam assigns to that shortcut. A few things to know:

- Steam must be **closed**, otherwise it overwrites the library changes when it exits.
- If Steam is detected, `zona install` asks whether to set up the integration.
- With `--steam`, `-p` is ignored, since Steam decides the prefix.
- With `--steam` and `-i`, the install directory must be inside a Steam library.

### Example

```sh
zona install            # full install with the defaults
zona mo2                # launch Mod Organizer 2 afterwards
```

During `install`, Anomaly is launched once (if needed) to generate the runtime
files MO2 expects. Close it when it reaches the main menu to continue.

## Configuration

Everything about *what* gets installed lives in [zona/config.toml](zona/config.toml):

- modpack version
- default install and archive directories
- Wine components and DLL overrides applied to the prefix
- the HUD (`clean`, `bhs`) and exes (`regular`, `mt`) variants
- every artifact: URL (HTTP, GitHub release or magnet link), filename, md5 and destination
- the modpack sources: a single archive or a multipart set (`one_of = "modpack"`),
  either of which is enough

## Development

```sh
git clone https://github.com/0xSickb0y/zona-installer
cd zona-installer
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
zona --help
```

## Layout

```
pyproject.toml
zona/
├── main.py                   # entry point, dispatches the commands
├── config.toml               # what gets installed (URLs, md5s, destinations)
├── core/
│   ├── config.py             # reads config.toml, defines the CLI with argparse
│   ├── log.py                # colored logging
│   └── utils.py              # helpers (yes_or_no)
├── download/
│   ├── __init__.py           # `zona download`
│   └── download.py           # HTTP, GitHub release and torrent (aria2c) downloads
├── setup/
│   ├── __init__.py           # `zona setup`: download, verify, directories, prefix
│   ├── path_ops.py           # path resolution, directory ops, Steam/tool discovery
│   ├── hash_verification.py  # md5 and GE-Proton sha512 checks
│   ├── modpack.py            # picks/recovers the single or multipart modpack source
│   ├── proton.py             # downloads and installs GE-Proton
│   └── runner.py             # dependency installs, prefix creation, running exes
├── install/
│   ├── __init__.py           # `zona install`: extraction and MO2 config
│   ├── extract.py            # 7z extraction
│   └── steam.py              # Steam shortcut, compat tool and prefix
├── mo2/
│   ├── __init__.py           # `zona mo2`: launch Mod Organizer 2
│   └── stylesheet.py         # `zona stylesheet` / --mo2-stylesheet: MO2 theme
└── templates/
    ├── ModOrganizer.ini      # MO2 config template
    └── nxmhandler.ini        # nxm link handler template
```

## Roadmap

- [x] Config file and CLI
- [x] Download archives and Anomaly (HTTP, GitHub releases, magnet)
- [x] md5 / sha512 verification
- [x] Extract archives
- [x] GE-Proton and prefix setup (winetricks / protontricks)
- [x] Mod Organizer 2 configuration and launch
- [x] Steam integration
- [ ] umu-launcher support (drop the Steam requirement)
- [ ] `zona delete`
- [ ] `--verbose` output
- [ ] Launch script and `.desktop` entry
- [ ] GUI
