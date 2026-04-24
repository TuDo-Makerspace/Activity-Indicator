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
# Usage: Run telegram-activity-indicator.py --help
# Brief Description: Sends TUDO activity info via a Telegram bot

import argparse
import configparser
import logging
import sys

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

parser = argparse.ArgumentParser(
    description="Send TUDO activity info via a Telegram bot"
)
parser.add_argument("--log_level", "-l", help="Log level", default="INFO")
parser.add_argument("--config_file", "-c", help="Config file", default="telegram.ini")
parser.add_argument("activity", choices=["open", "closed"], help="Activity status")
args = parser.parse_args()

logging.basicConfig(
    level=args.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read(args.config_file)

token = config["bot"]["Token"]
endpoint = TELEGRAM_API_URL.format(token=token)

for section in config.sections():
    if section == "bot":
        continue

    chat_id = config[section]["ChatID"]
    open_msg = config[section]["OpenMessage"]
    closed_msg = config[section]["ClosedMessage"]
    message = open_msg if args.activity == "open" else closed_msg

    response = requests.post(
        endpoint,
        data={"chat_id": chat_id, "text": message},
        timeout=10,
    )

    if response.status_code != 200:
        logger.error("Telegram API request failed: %s", response.text)
        sys.exit(1)

    payload = response.json()
    if not payload.get("ok"):
        logger.error("Telegram API rejected request: %s", payload)
        sys.exit(1)
