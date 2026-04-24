#!/usr/bin/env python3

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
# Description:
#       The following script contains the main code for the activity indicator.
#       It is executed as a background service by the activity-indicator systemd
#       service and monitors the activity switch, reports if a connection to the
#       internet is available, and executes a list of sub-services specified in the
#       config file.
#       This script must be run by the activity-indicator systemd service, and should not
#       be run manually. The GPIOs for the activity switch, as well as the connection
#       indicator LED must be specified in the config file.

import argparse
import configparser
import os
import pathlib
import shutil
import subprocess
import sys
import time

from enum import Enum

import gpiod
from gpiod.line import Bias, Direction, Value

# List of possible candidates to ping to check for internet connection
# Redundancy is good in case one of the candidates is down
# or much more likely, the uni's firewall is having a bad day
# again?
PING_CANDIDATES = [
    "8.8.8.8",
    "www.google.com",
    "google.com",
    "www.tu-berlin.de",
    "www.yahoo.com",
    "www.bing.com",
]

# Constants
SW_VER = "1.3.0"
AUTHOR = "Patrick Pedersen <ctx.xda@gmail.com>, TU-DO Makerspace <tu-do.net>"
LICENSE = "GPLv3"
SOURCE_CODE = "https://github.com/TU-DO-Makerspace/Activity-Indicator"

ADD_DATA_PATH = "/var/lib/activity-indicator"  # App data path
SAVED_STATE_PATH = ADD_DATA_PATH + "/saved_state"  # Path to save states to
RESET_WIFI_TIMEOUT = 60  # Seconds
DEFAULT_WIFI_INTERFACE = "wlan0"
GPIO_CHIP_PATH = "/dev/gpiochip0"


class ConLedState(Enum):
    OFF = 0
    RED = 1
    GREEN = 2


class Activity(Enum):
    CLOSED = 0
    OPEN = 1


class GpioController:
    HIGH = 1
    LOW = 0

    def __init__(self, chip_path: str, consumer: str = "activity-indicator"):
        self.chip_path = chip_path
        self.consumer = consumer
        self._requests = {}

    def setup_input_pullup(self, pin: int):
        self._requests[pin] = gpiod.request_lines(
            self.chip_path,
            consumer=self.consumer,
            config={
                pin: gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=Bias.PULL_UP,
                )
            },
        )

    def setup_output(self, pin: int):
        self._requests[pin] = gpiod.request_lines(
            self.chip_path,
            consumer=self.consumer,
            config={
                pin: gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    output_value=Value.INACTIVE,
                )
            },
        )

    def input(self, pin: int) -> int:
        return (
            self.HIGH
            if self._requests[pin].get_value(pin) == Value.ACTIVE
            else self.LOW
        )

    def output(self, pin: int, state: int):
        value = Value.ACTIVE if state == self.HIGH else Value.INACTIVE
        self._requests[pin].set_value(pin, value)

    def cleanup(self):
        for request in self._requests.values():
            request.release()
        self._requests.clear()


def print_journalctl(msg: str):
    print(msg)
    sys.stdout.flush()  # Needed, else print won't appear in journalctl log


def check_connection() -> bool:
    for candidate in PING_CANDIDATES:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", candidate],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return True
    return False


def set_con_led(
    gpio: GpioController,
    red_pin: int,
    green_pin: int,
    state: ConLedState,
):
    if state == ConLedState.OFF:
        gpio.output(red_pin, gpio.LOW)
        gpio.output(green_pin, gpio.LOW)
    elif state == ConLedState.RED:
        gpio.output(red_pin, gpio.HIGH)
        gpio.output(green_pin, gpio.LOW)
    elif state == ConLedState.GREEN:
        gpio.output(red_pin, gpio.LOW)
        gpio.output(green_pin, gpio.HIGH)


def error(gpio: GpioController, red_pin: int, green_pin: int, message: str):
    print_journalctl("FATAL ERROR: " + message)

    for _ in range(3):
        set_con_led(gpio, red_pin, green_pin, ConLedState.GREEN)
        time.sleep(0.5)
        set_con_led(gpio, red_pin, green_pin, ConLedState.OFF)
        time.sleep(0.5)
        set_con_led(gpio, red_pin, green_pin, ConLedState.RED)
        time.sleep(0.5)
        set_con_led(gpio, red_pin, green_pin, ConLedState.OFF)
        time.sleep(0.5)

    gpio.cleanup()
    sys.exit(1)


def gpio_to_activity(gpio_state: int) -> Activity:
    if gpio_state == GpioController.LOW:
        return Activity.OPEN
    return Activity.CLOSED


def save_state(path: str, state: Activity):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(state.name)


def saved_state(path: str):
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read().strip()

    if content == Activity.OPEN.name:
        return Activity.OPEN
    if content == Activity.CLOSED.name:
        return Activity.CLOSED

    print_journalctl("Unknown saved state: " + content)
    return None


def call_subservices(config: configparser.ConfigParser, new_activity: Activity) -> bool:
    success = True

    for section in config.sections():
        for option, command in config[section].items():
            if option not in {"openexec", "closedexec"}:
                continue

            should_run = (
                new_activity == Activity.OPEN and option == "openexec"
            ) or (
                new_activity == Activity.CLOSED and option == "closedexec"
            )

            if not should_run:
                continue

            service = f"{section}: {option}: {command}"
            print_journalctl("Executing: " + service)
            result = subprocess.run(command, shell=True, check=False)

            if result.returncode != 0:
                print_journalctl(
                    "Unexpected error while calling subservice: " + service
                )
                success = False

    return success


def wait_for_connection(timeout_s: int) -> bool:
    timeout = time.time() + timeout_s
    while not check_connection():
        if time.time() >= timeout:
            return False
        time.sleep(1)
    return True


def handle_connection(gpio: GpioController, red_pin: int, green_pin: int):
    if not check_connection():
        set_con_led(gpio, red_pin, green_pin, ConLedState.RED)
        if not wait_for_connection(RESET_WIFI_TIMEOUT):
            raise ConnectionError("No connection available after timeout")
    set_con_led(gpio, red_pin, green_pin, ConLedState.GREEN)


def run_network_command(cmd):
    return subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def reset_wifi(interface: str):
    if shutil.which("ip"):
        run_network_command(["ip", "link", "set", "dev", interface, "down"])
        run_network_command(["ip", "link", "set", "dev", interface, "up"])
        return

    if shutil.which("ifconfig"):
        run_network_command(["ifconfig", interface, "down"])
        run_network_command(["ifconfig", interface, "up"])
        return

    print_journalctl("No supported network utility found to reset WiFi")


parser = argparse.ArgumentParser(description="Handles the activity indicator")
parser.add_argument(
    "-c",
    "--config",
    default=os.path.dirname(os.path.realpath(__file__)) + "/activity-indicator.ini",
    type=str,
    help="Path to configuration file",
)
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config)

print("=== TU-DO Activity Indicator ===")
print("Version:\t" + SW_VER)
print("Author:\t\t" + AUTHOR)
print("License:\t" + LICENSE)
print("Source code:\t" + SOURCE_CODE)

try:
    pathlib.Path(ADD_DATA_PATH).mkdir(parents=True, exist_ok=True)
except Exception as exc:
    print_journalctl("FATAL ERROR: " + str(exc))
    sys.exit(1)

switch_pin = int(config["GPIO"]["Switch"])
red_pin = int(config["GPIO"]["ConLEDRed"])
green_pin = int(config["GPIO"]["ConLEDGreen"])
wifi_interface = config["GPIO"].get("WifiInterface", DEFAULT_WIFI_INTERFACE)

try:
    gpio = GpioController(GPIO_CHIP_PATH)
    gpio.setup_input_pullup(switch_pin)
    gpio.setup_output(red_pin)
    gpio.setup_output(green_pin)
except Exception as exc:
    print_journalctl("FATAL ERROR: Failed to initialize GPIO: " + str(exc))
    sys.exit(1)

if saved_state(SAVED_STATE_PATH) is None:
    try:
        save_state(SAVED_STATE_PATH, gpio_to_activity(gpio.input(switch_pin)))
    except Exception as exc:
        error(gpio, red_pin, green_pin, str(exc))

prev_state = saved_state(SAVED_STATE_PATH)
prev_wifi_state = True

while True:
    try:
        handle_connection(gpio, red_pin, green_pin)
    except ConnectionError:
        print_journalctl(
            "Failed to establish connection, resetting WiFi interface and retrying..."
        )
        reset_wifi(wifi_interface)
        prev_wifi_state = False
        continue

    if not prev_wifi_state:
        print_journalctl("Successfully re-established connection!")
        prev_wifi_state = True

    curr_state = gpio_to_activity(gpio.input(switch_pin))

    if curr_state != prev_state:
        try:
            print_journalctl(
                "Activity changed to: " + curr_state.name + ", calling subservices"
            )
            ret = call_subservices(config, curr_state)
            prev_state = curr_state
            save_state(SAVED_STATE_PATH, prev_state)

            if not ret:
                error(gpio, red_pin, green_pin, "One or more subservices failed")

            print_journalctl("All subservices executed successfully")
        except Exception as exc:
            error(gpio, red_pin, green_pin, str(exc))

    time.sleep(0.2)
