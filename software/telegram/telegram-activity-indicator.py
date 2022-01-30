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

# Description:
#       The following script sends TUDO activity info via a Telegram bot.
#       A configuration file (default config.ini) is used to store the
#       Telegram bot token, the target chat id's of all chats to be notified,
#       and the opening and closing messages to be sent to each individual chat.
#       See config.ini for a template of the configuration file.

import logging
import argparse
import configparser
import telegram

# Parse arguments
parser = argparse.ArgumentParser(description='Send TUDO activity info via a Telegram bot')
parser.add_argument('--log_level', '-l', help='Log level', default='INFO')
parser.add_argument('--config_file', '-c', help='Config file', default='telegram.ini')
parser.add_argument(
        'activity',
        choices=['open', 'closed'],
        help='Activity status'
)
args = parser.parse_args()

# Start logging
logging.basicConfig(level=args.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Read config file
config = configparser.ConfigParser()
config.read(args.config_file)

# Create telegram bot object
tkn = config['bot']['token']
bot = telegram.Bot(token=tkn)

# Send activity to each chat
for section in config.sections():
        if section == "bot":
                continue
        
        chat_id = config[section]['ChatID']
        open_msg = config[section]['OpenMessage']
        closed_msg = config[section]['ClosedMessage']

        if args.activity == "open":
                bot.send_message(chat_id=chat_id, text=open_msg)
        elif args.activity == "closed":
                bot.send_message(chat_id=chat_id, text=closed_msg)
