
#!/usr/bin/env bash
WORKING_DIR=$(realpath "$0")
WORKING_DIR=$(dirname $WORKING_DIR)

DESKTOP_ENTRY_NAME="Zona_test"
LAUNCH_SCRIPT_PATH="$HOME/Games/zona/launch.sh"

SKIP_VALIDATION=false

conty="conty_lite.sh"
conty_url="https://github.com/Kron4ek/Conty/releases/download/1.29.3/conty_lite.sh"

INSTALL_DIR="$HOME/.zona_conty"
TEMP_DIR="$INSTALL_DIR/tmp"
MD5_DIR="$INSTALL_DIR/md5"
LINK_DIR="$HOME/Games/zona"
CONTY="$INSTALL_DIR/$conty"
# this directory is treated as $HOME within conty:
CONTY_HOME="$INSTALL_DIR/home"
CONTY_VIRTUAL_PREFIX="$HOME/Games/umu/umu-default"
DRIVE_C="$INSTALL_DIR/home/Games/umu/umu-default/drive_c"

anomaly="Anomaly-1.5.3-Full.2.7z"
anomaly_url="https://www.moddb.com/$(wget -q -O- --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)" https://www.moddb.com/downloads/start/277404 | grep -Po '(?<=href="/)[^"]*' | head -1)"

demonized="STALKER-Anomaly-modded-exes_2026.8.17.zip"
demonized_url="https://github.com/themrdemonized/xray-monolith/releases/download/2026.8.17/STALKER-Anomaly-modded-exes_2026.8.17.zip"
mt_test="STALKER-Anomaly-modded-exes-MT-TEST_2026.8.17.zip"
mt_test_url="https://github.com/themrdemonized/xray-monolith/releases/download/2026.8.17/STALKER-Anomaly-modded-exes-MT-TEST_2026.8.17.zip"

mo2="Mod.Organizer-2.5.2.7z"
mo2_url="https://github.com/ModOrganizer2/modorganizer/releases/download/v2.5.2/Mod.Organizer-2.5.2.7z"

conty="conty_lite.sh"
conty_url="https://github.com/Kron4ek/Conty/releases/download/1.29.3/conty_lite.sh"

profiles="zona_profiles.7z"
zona_profiles_url="https://github.com/gtair/filehost-1/releases/download/v1.38/zona_profiles.7z"

clean="clean_hud.7z"
clean_hud_url="https://github.com/gtair/filehost-1/releases/download/v1.38/clean_hud.7z"
bhs="bhs_hud.7z"
bhs_hud_url="https://github.com/gtair/filehost-1/releases/download/v1.38/bhs_hud.7z"

zona=( "zona_multipart.7z.001" "zona_multipart.7z.002" "zona_multipart.7z.003" "zona_multipart.7z.004" "zona_multipart.7z.005" "zona_multipart.7z.006" "zona_multipart.7z.007" )
zona_multipart=("https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.001" "https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.002" "https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.003" "https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.004" "https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.005" "https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.006" "https://github.com/gtair/filehost-1/releases/download/v1.38/zona_multipart.7z.007")

md5sums_url="https://github.com/johnmnorman/filehost-1/releases/download/2/md5.zip"
md5sum_validation="7bda7295ed792e977de77e5d1a9e062d"

desktop_entry="[Desktop Entry]
Type=Application
Version=1.0
Name=Zona v1.38
Comment=Launch S.T.A.L.K.E.R Zona
Path=
Exec=$HOME/Games/zona/launch.sh
Terminal=true"

launch_script_conty="#!/usr/bin/env bash

INSTALL_DIR=$INSTALL_DIR

CONTY=\"\$INSTALL_DIR/conty_lite.sh\"
CONTY_VIRTUAL_PREFIX=\"\$HOME/Games/umu/umu-default\"
CONTY_HOME=\"\$INSTALL_DIR/home\"

HOME_DIR=\$CONTY_HOME \$CONTY umu-run \$CONTY_VIRTUAL_PREFIX/drive_c/mo2/ModOrganizer.exe"

### FUNCTION DECLARATIONS

function section_change() {
  echo ""
  echo "##########################################"
  echo "### $1"
  echo "##########################################"
  echo ""
}

function 1_or_2() {
  while true; do
    read -r -p "1 or 2 >> " hud
    case $hud in
      [1]* ) return "1";;
      [2]* ) return "2";;
      * ) echo "Please answer 1 or 2";;
    esac
  done
}

function y_or_n() {
  while true; do
    read -r -p "Is this ok? (y/n) >> " ok 
    case $ok in
      [Yy]* ) return "1";;
      [Nn]* ) return "2";;
      * ) echo "Please answer Y or N";;
    esac
  done
}

function wait_for_keypress() {
  echo
  read -r -p "Press Enter to continue."
  echo
}

function mkdir_if_absent() {
  if [ -f $1 ]; then
    echo "$1 exists, continuing."
  else
    echo "Creating new directory structure: $1"
    mkdir -p $1
  fi
}

function download() {
  #if [ -f $TEMP_DIR/$1 ]; then
  #  echo "$1: File failed checksum - removing."
  #  rm $TEMP_DIR/$1
  #fi
  echo "Downloading $1..."
  wget --continue --show-progress --output-document="$TEMP_DIR/$1" --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "$2"
  #checkmd5 $1 && echo "$1 OK, continuing." || download $1 $2
}

function download_checksums() {
  mkdir_if_absent "$INSTALL_DIR/md5"
  echo "Downloading checksums."
  rm "INSTALL_DIR/md5/*"


  download "md5.zip" $md5sums_url

  md5_md5=$(md5sum "$TEMP_DIR/md5.zip" | cut -d " " -f1)
  echo $md5_md5
  echo $md5sum_validation
  echo "Validating checksums..."
  if [ "$md5_md5" == "$md5sum_validation" ]; then
    echo "Checksums OK, continuing."
    return 0
  else
    echo "Could not obtain valid checksums."
    exit 1
  fi
}

function checkmd5() {
  checksum="$MD5_DIR/$1.md5"
  download="$TEMP_DIR/$1"
  if [ -f $download ]; then
    md5_to_test=$(cat $checksum | cut -d " " -f1)
    echo "Generating checksum for $download..."
    md5_from_file=$(md5sum $download | cut -d " " -f1)
    md5_results="Input: $md5_to_test\nFile:  $md5_from_file"
    if [[ $md5_to_test == $md5_from_file ]]
      then
        echo "checkmd5: $1 passed checksum."
        return 0
      else
        echo "checkmd5: $1 failed checksum!"
        exit 1
    fi
  else
    echo "checkmd5: $1 not found!"
    exit 1
  fi
}

function clean_install_dir() {
  yes | rm -r $INSTALL_DIR/home
  rm -r $INSTALL_DIR/md5
  rm -r $INSTALL_DIR/tmp
  rm $INSTALL_DIR/anomaly
  rm $INSTALL_DIR/mo2
  rm -r $INSTALL_DIR/md5
  rm $TEMP_DIR/md5.zip
  rm $INSTALL_DIR/launch.sh
  echo "Removed!"
}

### END FUNCTION DECLARATIONS

if [ "$1" == "clean" ]; then
  clean_install_dir
  rm $CONTY
  exit 0
elif [ "$1" == "--winetricks" ]; then
#  HOME_DIR=$CONTY_HOME $CONTY winetricks cmd d3dcompiler_47 d3dx10 d3dx11_43 d3dx9 dx8vb dxvk quartz vcrun2022
  HOME_DIR=$CONTY_HOME WINEPREFIX=$CONTY_VIRTUAL_PREFIX $CONTY winetricks cmd d3dcompiler_47 d3dx10 d3dx11_43 d3dx9 dx8vb quartz vcrun2022 dxvk
#  HOME_DIR=$CONTY_HOME $CONTY winetricks cmd d3dx9 dx8vb d3dcompiler_42 d3dcompiler_43 d3dcompiler_46 d3dcompiler_47 d3dx10_43 d3dx10 d3dx11_42 d3dx11_43 vcrun2022 dxvk quartz
  exit 0
elif [ "$1" == "final" ]; then
  final_prep
  exit 0
elif [ "$1" == "--skip-validation" ]; then
  SKIP_VALIDATION=true
fi

echo "Welcome to the Zona install script."
echo
echo "This script will take care of all the Wine/Proton stuff that has to happen for Zona to run on Linux. If you want to know more, it's in the readme."
echo
echo "Zona will be installed in this directory:"
echo "> $INSTALL_DIR"
echo
y_or_n
echo
if [ "$?" == "2" ]; then
  echo "Aborting."
  exit 1
fi
mkdir_if_absent $INSTALL_DIR

echo
echo "By default this script will place some symlinks and a launch script in $LINK_DIR."
y_or_n
echo
if [ "$?" == "2" ]; then
  while true; do

    read -r -p "Enter the path to a better directory >> " new_dir
    echo "The script will instead store symlinks and launch script in"
    echo "    $new_dir"
    echo "If it doesn't exist, it will be created."
    y_or_n
    if [ "$?" == "1" ]; then
      LINK_DIR="$new_dir"
      break
    fi
  done
fi
mkdir_if_absent $LINK_DIR
echo
echo "Which Zona settings do you want?"
echo "1) Clean HUD"
echo "2) BHS HUD"
1_or_2
hud_mode=$?
echo
echo "Zona requires modded exes from MrDemonized to run."
echo "Do you want the regular modded exes, or the multithreaded* ones?"
echo "Most people see a large performance boost with multithreading, but these are still in testing and may cause unexpected crashes or compatibility issues. Nevertheless recommended."
echo "1) Regular Demonized EXEs"
echo "2) Multithreaded Demonized EXEs"
1_or_2
exe_mode=$?

echo
echo "The installer will now download the required files. If the installer is interrupted, it should resume where it left off. If any files fail to validate, delete $TEMP_DIR and try again."
wait_for_keypress

section_change "DOWNLOADING REQUIRED FILES"

#mkdir_if_absent "$INSTALL_DIR/home"
mkdir_if_absent "$TEMP_DIR"
download_checksums
7z x -y -o"$INSTALL_DIR" "$TEMP_DIR/md5.zip"

### DOWNLOAD SECTION

download $anomaly $anomaly_url
download $profiles $zona_profiles_url
download $mo2 $mo2_url

download $conty $conty_url

if [ "$exe_mode" == "1" ]; then
  download $demonized $demonized_url
else
  download $mt_test $mt_test_url
fi

if [ "$hud_mode" == "1" ]; then
  download $clean $clean_hud_url
else
  download $bhs $bhs_hud_url
fi

for url in "${zona_multipart[@]}"; do
  filename=$(basename $url)
  download $filename $url
done

### CHECKSUM SECTION
section_change "VALIDATING DOWNLOADED FILES"

if [ $SKIP_VALIDATION == false ]; then
  checkmd5 $anomaly 
  checkmd5 $profiles 
  checkmd5 $mo2 

  checkmd5 $conty

  if [ "$exe_mode" == "1" ]; then
    checkmd5 $demonized 
  else
    checkmd5 $mt_test 
  fi
  mkdir_if_absent "$MD5_DIR"

  if [ "$hud_mode" == "1" ]; then
    checkmd5 $clean
  else
    checkmd5 $bhs
  fi

  for url in "${zona_multipart[@]}"; do
    filename=$(basename $url)
    checkmd5 $filename 
  done
else
  echo "Skipping validation..."
fi

section_change "PREPARING FILESYSTEM"

echo "Moving $conty into $INSTALL_DIR from $TEMP_DIR ..."
cp "$TEMP_DIR/$conty" "$INSTALL_DIR"
echo "Making $conty executable ..."
chmod +x $CONTY
echo "Attempting to set up wineprefix in $CONTY_HOME..."
mkdir_if_absent "$CONTY_HOME"
HOME_DIR=$CONTY_HOME $CONTY umu-run ""
mkdir_if_absent "$DRIVE_C/mo2/profiles"
mkdir_if_absent "$DRIVE_C/mo2/mods"
mkdir_if_absent "$DRIVE_C/anomaly"
#FIXME mkdir_if_absent "$HOME/Games/zona/"
if [ -d "$HOME/Games/zona/mo2_folder" ]; then
  echo "Removing old symlink mo2_folder..."
  rm "$HOME/Games/zona/mo2_folder"
fi
if [ -d "$HOME/Games/zona/anomaly_folder" ]; then
  echo "Removing old symlink anomaly_folder..."
  rm "$HOME/Games/zona/anomaly_folder"
fi
if [ -d "$HOME/Games/zona/virtual_home" ]; then
  echo "Removing old symlink virtual_home..."
  rm "$HOME/Games/zona/virtual_home"
fi
echo "Making symbolic link to $CONTY_HOME ..."
ln -s "$CONTY_HOME" "$HOME/Games/zona/virtual_home"
echo "Making symbolic link to $DRIVE_C/mo2 ..."
ln -s "$DRIVE_C/mo2" "$HOME/Games/zona/mo2_folder"
echo "Making symbolic link to $DRIVE_C/anomaly ..."
ln -s "$DRIVE_C/anomaly" "$HOME/Games/zona/anomaly_folder"

section_change "EXTRACTING FILES"

echo "Extracting $anomaly to $DRIVE_C/anomaly..."
7z x -y -o"$DRIVE_C/anomaly" $TEMP_DIR/$anomaly

if [ "$exe_mode" == "1" ]; then
  echo "Extracting $demonized to $DRIVE_C/anomaly..."
  7z x -y -o"$DRIVE_C/anomaly" $TEMP_DIR/$demonized
else
  echo "Extracting $mt_test to $DRIVE_C/anomaly..."
  7z x -y -o"$DRIVE_C/anomaly" $TEMP_DIR/$mt_test
fi

echo "Extracting $mo2 to $DRIVE_C/mo2 ..."
7z x -y -o"$DRIVE_C/mo2" $TEMP_DIR/$mo2

echo "Extracting $profiles to $DRIVE_C/mo2/profiles ..."
7z x -y -o"$DRIVE_C/mo2/profiles" $TEMP_DIR/$profiles
echo "Extracting ${zona[0]} to $DRIVE_C/mo2 ..."
7z x -y -o"$DRIVE_C/mo2" "$TEMP_DIR/${zona[0]}"

section_change "IMPORTING ZONA SETTINGS"

if [ "$hud_mode" == "1" ]; then
  7z x -y -o"$TEMP_DIR" "$TEMP_DIR/$clean"
  cp -r "$TEMP_DIR/Clean Hud/appdata" "$DRIVE_C/anomaly/"
  cp -r "$TEMP_DIR/Clean Hud/gamedata" "$DRIVE_C/anomaly/"
else
  7z x -y -o"$TEMP_DIR" "$TEMP_DIR/$bhs"
  cp -r "$TEMP_DIR/Bhs Hud/appdata" "$DRIVE_C/anomaly/"
  cp -r "$TEMP_DIR/Bhs Hud/gamedata" "$DRIVE_C/anomaly/"
fi

section_change "FINAL PREP"

echo "Adding a launch script to install directory."
echo "$launch_script_conty" > "$LAUNCH_SCRIPT_PATH"
chmod +x $LAUNCH_SCRIPT_PATH

echo "$desktop_entry" > "$HOME/.local/share/applications/$DESKTOP_ENTRY_NAME.desktop"
echo "The installer will now run winetricks to install essential Wine components. When installers pop up, Agree to any terms of service and click OK or Install."
echo
echo "HINT - if winetricks quits unexpectedly or hangs, or you get shader compilation issues, try this command to run winetricks again:"
echo
echo "    $(basename $0) --winetricks"

wait_for_keypress

HOME_DIR=$CONTY_HOME WINEPREFIX=$CONTY_VIRTUAL_PREFIX $CONTY winetricks cmd d3dcompiler_47 d3dx10 d3dx11_43 d3dx9 dx8vb quartz vcrun2022 dxvk

echo
echo "Zona installation finished. To launch Zona, run $LAUNCH_SCRIPT_PATH"
echo
echo "If you wish to install additional mods on top of Zona, you must drop their archives into $CONTY_HOME in order to make them visible to Mod Organizer! A symlink to this folder has been added at $HOME/Games/zona/virtual_home"
echo
echo "Thank you for playing Zona!"
exit 0
