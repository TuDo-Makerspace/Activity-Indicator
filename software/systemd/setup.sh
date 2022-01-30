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
# Brief Description: Sets up the activity-indicator systemd service
# Usage: sudo ./setup.sh [install|uninstall]

# Get directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

if [ "$1" = "install" ]; then
        systemctl stop activity-indicator.service
        rm -rf /etc/systemd/system/activity-indicator.service
        cp "$SCRIPT_DIR/activity-indicator.service" /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable activity-indicator.service
        systemctl start activity-indicator.service
elif [ "$1" = "uninstall" ]; then
        systemctl stop activity-indicator.service
        systemctl disable activity-indicator.service
        rm -rf /etc/systemd/system/activity-indicator.service
        systemctl daemon-reload
else
        echo "Usage: sudo ./setup.sh [install|uninstall]"
fi


