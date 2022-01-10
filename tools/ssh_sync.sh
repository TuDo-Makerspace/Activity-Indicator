#!/usr/bin/env bash

# This script is used to sync the remote project directory on
# the RPI with the local project directory. In the other words,
# this script pushes the local project directory to the RPI.

# Get directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT="$SCRIPT_DIR/.."

if [ -z "$1" ]; then
  echo "Usage: $0 <hostname>"
  exit 1
fi

HOSTNAME="$1"

cd "$PROJECT_ROOT"
PROJECT_DIR_NAME="$(basename "$PWD")"

# Check if ssh connection can be established
ssh -q -o BatchMode=yes "$HOSTNAME" exit

if [ $? != "0" ]; then
    echo "$0: Connection to remote device failed"
    exit -1
fi

# Remove remote project folder and push local project folder
ssh "$HOSTNAME" rm -rf "\$HOME/$PROJECT_DIR_NAME"
scp -r "$PWD" "$HOSTNAME":"\$HOME/"