# Get directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

systemctl stop switch_monitor.service
rm -rf /etc/systemd/system/switch_monitor*.service
cp "$SCRIPT_DIR/switch_monitor.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable switch_monitor.service
systemctl start switch_monitor.service
