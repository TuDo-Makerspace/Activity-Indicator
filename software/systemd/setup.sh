# Get directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

if [ -z "$1" ]; then
  echo "Usage: $0 <Activity switch pin>"
  exit 1
fi

systemctl stop switch_monitor@\*.service
rm -rf /etc/systemd/system/switch_monitor*.service
cp "$SCRIPT_DIR/switch_monitor@.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable switch_monitor@"$1".service
systemctl start switch_monitor@"$1".service
