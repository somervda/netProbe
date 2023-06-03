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
from netLogger import NetLogger

import shared

hosts: Hosts
netLogger: NetLogger


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


def scheduler():
    global hosts
    global netLogger
    # Perform scheduling of tests on next host
    nextHostToTest = hosts.findNextHostToTest()
    host = hosts.getHost(nextHostToTest)
    print(host["address"])
    hostTests = hosts.getHostTests(nextHostToTest)
    if "ping" in host:
        ping = host["ping"]
        # We have ping info
        if ping["active"]:
            if hostTests["lastPing"] + (ping["intervalMinutes"] * 60) < time.time():
                hostTests["lastPing"] = time.time()
                # We are due to run the ping test
                pingResult = uping.ping(host["address"], size=16)
                if pingResult == None:
                    netLoggerRecord = {
                        "id": host["id"], "type": "ping",  "success": False}
                else:
                    netLoggerRecord = {
                        "id": host["id"], "type": "ping", "rtl": int(pingResult[0]), "success": True}
                netLogger.writeloggerRecord(netLoggerRecord)

    if "bing" in host:
        bing = host["bing"]
        # We have ping info
        if bing["active"]:
            if hostTests["lastBing"] + (bing["intervalMinutes"] * 60) < time.time():
                hostTests["lastBing"] = time.time()
                # We are due to run the bing test
                bingResult = ubing.bing(
                    host["address"], maxSize=1400, quiet=True)
                netLoggerRecord = {
                    "id": host["id"], "type": "bing", "bps": bingResult[0], "rtl":  int(bingResult[1]),  "success": True}
                netLogger.writeloggerRecord(netLoggerRecord)

    if "web" in host:
        web = host["web"]
        # We have ping info
        if web["active"]:
            if hostTests["lastWeb"] + (web["intervalMinutes"] * 60) < time.time():
                hostTests["lastWeb"] = time.time()
                # We are due to run the web test
                # Test host responds before trying web request, otherwise it ties things up for 60 sec
                pingResult = uping.ping(host["address"], size=16)
                if pingResult != None:
                    if web["https"]:
                        target = "https://"
                    else:
                        target = "http://"
                    target += host["address"] + web["url"]
                    webResult = uwebPage.webPage(
                        target, web["match"], quiet=True)
                    if webResult == None:
                        netLoggerRecord = {
                            "id": host["id"], "type": "web",  "success": False}
                    else:
                        netLoggerRecord = {"id": host["id"], "type": "web", "ms": int(webResult[0]),
                                           "match": webResult[1], "status": webResult[2], "success": True}
                    netLogger.writeloggerRecord(netLoggerRecord)
    # Update the last update times
    hosts.updateHostTests(hostTests)
    print("sleeping...")
    time.sleep(30)


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
    netLogger = NetLogger()

    for loop in range(2000):
        print("   * ", loop, " *")
        scheduler()
    # print(netLogger.getHistory(739022128, 2, "ping"))

    print("")
    print("")
