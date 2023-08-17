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

# This file is script is used as a place holder until a the
# website has been fully migrated to the new one. It is therefor
# subject to change.

import argparse
import configparser
import requests

# POST endpoint to set the activity status
POST_ENDPOINT = "/api/activityIndicator"

# Parse arguments
parser = argparse.ArgumentParser(
    description="Updates the activity status on the new website"
)
parser.add_argument(
    "--config_file", "-c", help="Config file", default="new_website.ini"
)
parser.add_argument("activity", choices=["open", "closed"], help="Activity status")
args = parser.parse_args()

# Read config file
config = configparser.ConfigParser()
config.read(args.config_file)

uname = config["api"]["Username"]
pwd = config["api"]["Password"]
url = config["api"]["URL"]

print(url + POST_ENDPOINT)
print(uname, pwd)

# Send POST request to set the activity status
response = requests.post(
    url + POST_ENDPOINT,
    data={"open": "true" if args.activity == "open" else "false"},
    auth=(uname, pwd),
)

# Print error message if POST request failed
if response.status_code != 200:
    print("new_website.py: Request Failed: " + response.text, response)
