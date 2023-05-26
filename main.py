import os
import time
# import io
# import sys
import uping
import ubing
import uwebPage

import network
import machine
import ntptime

from netconfig import NetConfig
from hosts import Hosts

import shared


def connect():
    netConfig = NetConfig()
    global net_if
    led = machine.Pin(33, machine.Pin.OUT)
    led.on()
    if netConfig.useWiFi:
        net_if = network.WLAN(network.STA_IF)
    else:
        # Connection details for a ESP32-Gateway board from Olimex (Ethernet connection)
        # Note: clock_mode=network.ETH_CLOCK_GPIO17_OUT is no longer needed for latest OLIMEX
        # micropython builds
        net_if = network.LAN(mdc=machine.Pin(23), mdio=machine.Pin(18), power=machine.Pin(
            12), phy_type=network.PHY_LAN8720, phy_addr=0)
    net_if.active(True)
    if not netConfig.dhcp:
        # Use netConfig.json settings for ifconfig if not dhcp
        ifconfig = (netConfig.IP, netConfig.netmask,
                    netConfig.gateway, netConfig.dns)
        net_if.ifconfig(ifconfig)
    if netConfig.useWiFi:
        net_if.connect(netConfig.wifiSSID, netConfig.wifiPassword)
    while not net_if.isconnected() or net_if.status() == 0 or net_if.ifconfig()[0] == "0.0.0.0":
        print(".", end="")
        time.sleep(.5)
        led.off()
        time.sleep(.5)
        led.on()

    ntptime.timeout = 2
    if netConfig.ntp != "":
        ntptime.host = netConfig.ntp
    ntptime.settime()
    # Fast blink to indicate good connection
    for x in range(10):
        time.sleep(.1)
        led.on()
        time.sleep(.1)
        led.off()


if __name__ == '__main__':
    # Check if we have a SD card plugged in
    try:
        sd = machine.SDCard(slot=1, width=1, sck=machine.Pin(
            14), miso=machine.Pin(2), mosi=machine.Pin(15))
        os.mount(sd, '/sd')
    except OSError:
        shared.hasSDCard = False
    connect()
    print(net_if.ifconfig())
    hosts = Hosts()
    print("maxId:", hosts.maxId)
    print("Host2:", hosts.getHost(2))
    hosts.removeHost(6)
    newHost = {
        "name": "192.168.1.1",
        "description":"Fios Router4",
        "ping": {
            "active": True,
            "intervalMinutes": 5
        },
        "bing": {
            "active": False,
            "intervalMinutes": 5
        }
    }
    hosts.addHost(newHost )

    print("")
    print("")
