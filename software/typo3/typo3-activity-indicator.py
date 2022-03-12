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
# Usage: Run typo3-acitivty-indicator.py --help
# Brief Description:
# 	Updates the activity status on a TYPO3 website with the Activity Indicator extension
# Description:
# 	The following script is used to update the Activity status on a TYPO3 website with
# 	the Activity Indicator extension (github.com/TU-DO-Makerspace/TYPO3-ActivityIndicator)
# 	installed.
# 	
# 	The TYPO3 Activity Indicator extension exposes the following REST API endpoints to set 
# 	and retrieve the Activity status:
#
#		- GET /api/ActivityIndicator/activity (returns the current activity status)
#		- POST /api/ActivityIndicator/activity/{open|closed} (sets the activity status and requires HTTP Basic Auth)
#
#	Only a FE user of the API group can use the POST endpoint to set the activity status, hence the 
# 	credentials for one must be provided in the typo3.ini configuration file.

import argparse
import configparser
import requests

# POST endpoint to set the activity status
POST_ENDPOINT = '/api/ActivityIndicator/activity/'

# Parse arguments
parser = argparse.ArgumentParser(description='Updates the activity status on a TYPO3 website with the Activity Indicator extension')
parser.add_argument('--config_file', '-c', help='Config file', default='typo3.ini')
parser.add_argument(
        'activity',
        choices=['open', 'closed'],
        help='Activity status'
)
args = parser.parse_args()

# Read config file
config = configparser.ConfigParser()
config.read(args.config_file)

# Read config file
uname = config['api']['Username']
pwd = config['api']['Password']
url = config['api']['URL']

# Send POST request to set the activity status
response = requests.post(
	url + POST_ENDPOINT + args.activity,
	auth=(uname, pwd)
)

# Print error message if POST request failed
if response.status_code != 200:
	print("typo3-activity-indicator.py: Request Failed: " + response.text)