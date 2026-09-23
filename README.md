ZONA INSTALL SCRIPT
written by jmnorman

How it works:

For the sake of simplicity, we use Conty to run Zona. Conty (authored by Kron4ek) is a prepackaged Linux container that contains Wine, Proton, and everything that Wine and Proton depend on to run. Inside of Conty is a prepackaged Proton runner called umu-run, and we use that to launch ModOrganizer and thus run Zona. Conty is not itself necessary to run Zona, but is provided as a convenience for users who are not familiar with the idiosyncrasies of Wine and Windows emulation. It provides a plug-and-play solution that we hope will make Zona more widely accessible.

Once Zona is installed, you will find a symlink to your Anomaly install at ~/Games/zona/anomaly and a symlink to your Mod Organizer install at ~/Games/zona/mo2. You might not need to touch those at all, but they're there in case you need to delete your shader cache manually or do anything else in there. The installer will place a .desktop file in ~/.local/share/applications so that most application launchers will list "Zona v1.38" as a new application. If you need it, the launch script lives at ~/Games/zona/launch.sh. When you run ModOrganizer for initial setup, you will find your anomaly and mo2 folders under the C:/ drive. Set up ModOrganizer for a portable install and point it to the C:/anomaly folder. Otherwise, default settings should be fine. When ModOrganizer loads and is ready to launch, make sure to select a Zona profile in the dropdown at the top of the mod load order list, or else Mod Organizer will not have any mods enabled.

ADVANCED USERS:
Your Zona install will live inside ~/.zona_conty/home/Games/umu/umu-default/, which is an ordinary wineprefix created by umu's own custom flavor of Proton. You'll find it under drive_c. Conty treats ~/.zona_conty/home as a virtual $HOME directory, and so, in Conty's eyes, ~/.zona_conty/home/Games/umu/umu-default is seen as ~/Games/umu/umu-default. Conty won't be able to see outside of ~/.zona_conty/home, and any filepath inside of ~/.zona_conty/home must be passed to Conty as relative to your actual $HOME directory. This is only relevant if you want to call Conty yourself or modify anything about its launch parameters or your own virtual Conty filesystem - check Kron4ek's github for more info. (https://github.com/Kron4ek/Conty)

If you'd rather use your own preferred flavor of Proton through your own Proton runner, that's entirely possible - when you invoke your runner, set WINEPREFIX="$HOME/.zona_conty/home/Games/umu/umu-default" and launch ModOrganizer. The author of this script has had the best luck running Zona with UMU-Proton-10.0-4, which is what Conty will use by default. YMMV. 

If you wish to launch Conty's own umu-run with another flavor of Proton, drop the Proton folder into ~/.zona_conty/home/.local/share/Steam/compatibilitytools.d/ and in your launch script for Zona, and add a PROTONPATH environment variable to the invocation of Conty in launch.sh to point to "$HOME/.local/share/Steam/compatibilitytools.d/your_proton_folder". 

And as always, if you wanna do any of this advanced stuff, make backups of anything critical and have a plan to revert your changes. I cannot guarantee that your changes won't break your OS, brick your computer, and/or kickstart the robot apocalypse.
