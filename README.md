ZONA INSTALL SCRIPT
written by jmnorman

How it works:

Launch the script in a terminal. Answer the prompts as you see fit. The script will download and extract the necessary files, set up Wine, and add some helpful symlinks and a launch script. Do not close out until the installer says INSTALLATION FINISHED. The installer should pick back up where it left off if you do close it for any reason. 

For the sake of simplicity, we use Conty to run Zona. Conty (authored by Kron4ek) is a prepackaged Linux container that contains Wine, Proton, and everything that Wine and Proton depend on to run. Inside of Conty is a prepackaged Proton runner called umu-run, and we use that to launch ModOrganizer and thus run Zona. Conty is not itself necessary to run Zona, but is provided as a convenience for users who are not familiar with the idiosyncrasies of Wine and Windows emulation. It provides a plug-and-play solution that we hope will make Zona more widely accessible.

Once Zona is installed, you will find a symlink to your Anomaly install at ~/Games/zona/anomaly by default and a symlink to your Mod Organizer install at ~/Games/zona/mo2_folder by default. You might not need to touch those at all, but they're there in case you need to delete your shader cache manually or do anything else.

The installer will place a .desktop file in ~/.local/share/applications if that folder is present, or otherwise on your desktop at ~/Desktop. Most application launchers will read this file and show Zona as "Zona v1.38".

If you need it, the launch script lives at ~/Games/zona/launch.sh by default, or else wherever you set it to be installed. When you run ModOrganizer for initial setup, you will find your anomaly and mo2 folders under the C:/ drive. Once you've gotten Mod Organizer open, you should be able to follow the normal install procedure for Zona listed in the Discord. When ModOrganizer loads and is ready to launch, make sure to select a Zona profile in the dropdown at the top of the mod load order list, or else Mod Organizer will not have any mods enabled.

FAQ:

How do I install more mods?

- Wherever your installer placed the symlinks and launch script (defaults to $HOME/Games/zona) there should be a folder called virtual_home. Stick the mod archive in there, and it will be visible from within Mod Organizer when you use the install mod dialog and navigate to your home directory. virtual_home is a virtual home directory that Conty uses to keep its stuff separate from your actual home directory.

I get a weird error in my Mod Organizer log or in the terminal, but the game still works?

- Awesome! If the game runs, it's probably no big deal. Xalia is a common component to give errors, but it isn't something that Stalker needs anyway.

INFO FOR ADVANCED USERS:

Your Zona install will live inside ~/.zona_conty/home/Games/umu/umu-default/, which is an ordinary wineprefix created by umu's own custom flavor of Proton. You'll find it under drive_c. Conty treats ~/.zona_conty/home as a virtual $HOME directory, and so, in Conty's eyes, ~/.zona_conty/home/Games/umu/umu-default is seen as ~/Games/umu/umu-default. Conty won't be able to see outside of ~/.zona_conty/home, and any filepath inside of ~/.zona_conty/home must be passed to Conty as relative to your actual $HOME directory. This is only relevant if you want to call Conty yourself or modify anything about its launch parameters or your own virtual Conty filesystem - check Kron4ek's github for more info. (https://github.com/Kron4ek/Conty)

If you'd rather use your own preferred flavor of Proton through your own Proton runner, that's entirely possible - when you invoke your runner, set WINEPREFIX="$HOME/.zona_conty/home/Games/umu/umu-default" and launch ModOrganizer. The author of this script has had the best luck running Zona with UMU-Proton-10.0-4, which is what Conty will use by default. YMMV. 

If you wish to launch Conty's own umu-run with another flavor of Proton, drop the Proton folder into ~/.zona_conty/home/.local/share/Steam/compatibilitytools.d/ and in your launch script for Zona, and add a PROTONPATH environment variable to the invocation of Conty in launch.sh to point to "$HOME/.local/share/Steam/compatibilitytools.d/your_proton_folder". 

And as always, if you wanna do any of this advanced stuff, make backups of anything critical and have a plan to revert your changes. I cannot guarantee that your changes won't break your OS, brick your computer, and/or kickstart the robot apocalypse.
