#!/bin/bash

# colored output helper functions
NC='\e[0m'
echoGreen() {
    echo -n -e "\e[0;32m$1${NC}"
}
echoYellow() {
    echo -n -e "\e[0;33m$1${NC}"
}
echoRed() {
    echo -n -e "\e[0;31m$1${NC}"
}

getRmqPass() {
    echoYellow "Create password for rabbitmq: "
    read -s rmq_pass
    echo ""

    echoYellow "Confirm password for rabbitmq: "
    read -s rmq_pass_confirm
    echo ""

    if [ "$rmq_pass" != "$rmq_pass_confirm" ]; then
        echoRed "Passwords do not match, try again\n"
        getRmqPass
    fi
}

git_location="/home/hakan/parosReceiver"

# install rabbitmq server
echoGreen "Installing APT Prerequisites...\n"
apt-get update && apt-get -y upgrade
apt-get -y install erlang rabbitmq-server python3-pip

# enable and start rabbitmq server
echoGreen "Starting rabbitmq server...\n"
systemctl enable rabbitmq-server
systemctl start rabbitmq-server

# enable rabbitmq management plugin
#rabbitmq-plugins enable rabbitmq_management

echoYellow "Pick a username for rabbitmq [paros]: "
read rmq_user
rmq_user=${rmq_user:-paros}

getRmqPass

rabbitmqctl add_user $rmq_user $rmq_pass
rabbitmqctl set_user_tags $rmq_user administrator
rabbitmqctl set_permissions -p / $rmq_user "." "." "."

echoGreen "Creating system files...\n"

cp $git_location/parosReceiver.service /etc/systemd/system/parosReceiver
systemctl daemon-reload

echoYellow "Should receiver be autostarted on boot (y/n)? "
read enable_logger
if [ "$enable_logger" = "y" ]; then
    systemctl enable parosReceiver
else
    systemctl disable parosReceiver
fi