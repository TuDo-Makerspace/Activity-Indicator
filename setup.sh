#!/usr/bin/env bash

# Copyright (C) 2022 Patrick Pedersen, TUDO Makerspace

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Author: Patrick Pedersen <ctx.xda@gmail.com>
# Brief Description: Sets up the activity-indicator
# Usage: See ./setup.sh help

BIN_DIR=/usr/local/sbin/activity-indicator
PY_SCRIPTS_DIR=/usr/share/pyshared/activity-indicator
CFG_DIR=/var/lib/activity-indicator

# Get directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR="$SCRIPT_DIR"

APT_DEPENDENCIES="python3 python3-pip python3-dev python3-requests"

emu_mount_fixed_cpuinfo() {
	mkdir -p $CFG_DIR
	cp /proc/cpuinfo $CFG_DIR/cpuinfo
	sed -i '/^Hardware\t*:.*/a Revision\t: a02082' $CFG_DIR/cpuinfo

	mnt_cmd="mount -v --bind $CFG_DIR/cpuinfo /proc/cpuinfo"

	if ! grep -q "^$mnt_cmd" /etc/rc.local; then
		sed -i '/^exit 0/i\'"$mnt_cmd" /etc/rc.local
		bash -c "$mnt_cmd"
	fi
}

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

if [ "$1" == "dependencies" ]; then
        echo "Installing apt dependencies..."
        apt install -y $APT_DEPENDENCIES

        if [ $? -ne 0 ]; then
                echo "Failed to install apt dependencies"
                exit 1
        fi

        echo "Installing pip dependencies..."
        pip3 install -r "$PROJECT_DIR/requirements.txt"

        if [ $? -ne 0 ]; then
                echo "Failed to install pip dependencies"
                exit 1
        fi

        echo "Dependencies successfully installed"
elif [[ "$1" == "install" || "$1" == "install-emu" ]]; then
	echo "Installing activity-indicator..."

	if [ "$1" == "install-emu" ]; then
		echo "Mounting fixed cpuinfo for GPIO libraries to work..."
		emu_mount_fixed_cpuinfo
		echo "Mounted fixed cpuinfo!"
	fi

        cp -v $PROJECT_DIR/software/activity-indicator.py $BIN_DIR

        mkdir -p $PY_SCRIPTS_DIR
        mkdir -p $PY_SCRIPTS_DIR/telegram
        cp -v $PROJECT_DIR/software/telegram/*.py $PY_SCRIPTS_DIR/telegram/

	mkdir -p $PY_SCRIPTS_DIR/typo3
	cp -v $PROJECT_DIR/software/typo3/*.py $PY_SCRIPTS_DIR/typo3/

	mkdir -p $PY_SCRIPTS_DIR/new_website
	cp -v $PROJECT_DIR/software/new_website/*.py $PY_SCRIPTS_DIR/new_website/

        mkdir -p $CFG_DIR
        cp -v $PROJECT_DIR/software/activity-indicator.ini $CFG_DIR/activity-indicator.ini
        cp -v $PROJECT_DIR/software/telegram/telegram.ini $CFG_DIR/telegram.ini
	cp -v $PROJECT_DIR/software/typo3/typo3.ini $CFG_DIR/typo3.ini
	cp -v $PROJECT_DIR/software/new_website/new_website.ini $CFG_DIR/new_website.ini

        echo "Setting up systemd service..."
        bash $PROJECT_DIR/software/systemd/setup.sh install

        echo "Installation complete, the activity switch should be running now!"
elif [ "$1" == "uninstall" ]; then
        echo "Uninstalling..."
        rm -v -rf $BIN_DIR
        rm -v -rf $PY_SCRIPTS_DIR
        rm -v -rf $CFG_DIR
        rm -v -rf /etc/systemd/system/activity-indicator.service

        echo "Disabling systemd service"
        bash $PROJECT_DIR/software/systemd/setup.sh uninstall

        echo "Uninstallation complete"
else
        if [ "$1" != 'help' ]; then
                echo "Unknown or missing argument"
                echo
        fi
        echo "Usage: ./setup.sh [help|install|uninstall|dependencies]"
        echo
        echo -e "\thelp:\t\tDisplays this message"
        echo -e "\tinstall:\tSets up and enables the Activity Indicator"
        echo -e "\tinstall-emu:\tSets up and enables the Activity Indicator on a QEMU instance"
        echo -e "\tuninstall:\tStops and removes the Activity Indicator software"
        echo -e "\tdependencies:\tInstalls required software dependencies"
        echo
fi
