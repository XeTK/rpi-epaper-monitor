#! /bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

apt-get update
apt-get -y install git python3-pip

git clone https://github.com/elad661/rpi_epd2in7.git

cd rpi_epd2in7

eval $(cat README.md | grep apt-get | head -n 1 | cut -d '`' -f 2 | sed 's/install/-y install/')

pip3 install -r requirements.txt

python3 setup.py install

cd ..

pip3 install uptime
pip3 install netifaces

ROOT_DIRECTORY=$(pwd) envsubst < screen_example.service > screen.service

chmod 755 screen.service
chown root:root screen.service

cp screen.service /etc/systemd/system/

systemctl enable screen
systemctl start screen