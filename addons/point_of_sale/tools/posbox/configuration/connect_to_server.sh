#!/usr/bin/env bash

# Write the server configuration
function connect () {
	SERVER="${1}"
	CURRENT_SERVER_FILE=/home/pi/odoo-remote-server.conf
	HOSTS=/root_bypass_ramdisks/etc/hosts
	HOST_FILE=/root_bypass_ramdisks/etc/hostname
	HOSTNAME="$(hostname)"
	IOT_NAME="${2}"
	IOT_NAME="${IOT_NAME//[^[:ascii:]]/}"
	IOT_NAME="${IOT_NAME//[^a-zA-Z0-9-]/}"
	sudo mount -o remount,rw /
	sudo mount -o remount,rw /root_bypass_ramdisks
	if [ ! -z "${1}" ]
	then
		echo "${SERVER}" > ${CURRENT_SERVER_FILE}
	fi
	if [ ! -z "${2}" ]
	then
		sudo sed -i "s/${HOSTNAME}/${IOT_NAME}/g" ${HOSTS}
		echo "${IOT_NAME}" > /tmp/hostname
		sudo cp /tmp/hostname "${HOST_FILE}"
		sudo hostname "${IOT_NAME}"
	fi
	sudo mount -o remount,ro /
	sudo mount -o remount,ro /root_bypass_ramdisks
	sudo reboot
}

connect "${1}" "${2}" &