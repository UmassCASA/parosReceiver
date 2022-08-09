#!/bin/bash
source config.sh

# install rabbitmq server
apt-get update && apt-get upgrade
apt-get install erlang rabbitmq-server

# enable and start rabbitmq server
systemctl enable rabbitmq-server
systemctl start rabbitmq-server

# enable rabbitmq management plugin
#rabbitmq-plugins enable rabbitmq_management

rabbitmqctl add_user $rabbitmq_user $rabbitmq_pass
rabbitmqctl set_user_tags $rabbitmq_user administrator
rabbitmqctl set_permissions -p / $rabbitmq_user "." "." "."