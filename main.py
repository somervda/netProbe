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

hosts: Hosts


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
    # Perform scheduling of tests on next host
    nextHostToTest = hosts.findNextHostToTest()
    host = hosts.getHost(nextHostToTest)
    hostTests = hosts.getHostTests(nextHostToTest)
    if "ping" in host:
        web = host["ping"]
        # We have ping info
        if web["active"]:
            if hostTests["lastPing"] + (web["intervalMinutes"] * 60) < time.time():
                hostTests["lastPing"] = time.time()
                # We are due to run the ping test
                webResult = uping.ping(host["address"], size=16)
                if webResult == None:
                    print("Ping failed to ", host["address"])
                else:
                    print("Ping ", host["address"], "rtl:", webResult[0], " ttl:",
                          webResult[1], " size:", webResult[2])

    if "bing" in host:
        web = host["bing"]
        # We have ping info
        if web["active"]:
            if hostTests["lastBing"] + (web["intervalMinutes"] * 60) < time.time():
                hostTests["lastBing"] = time.time()
                # We are due to run the bing test
                webResult = ubing.bing(
                    host["address"], maxSize=1400, quiet=True)
                if webResult == None:
                    print("Bing failed to ", host["address"])
                else:
                    print("Bing ", host["address"], " bps:", webResult[0], " rtl:",
                          webResult[1],)
    if "web" in host:
        web = host["web"]
        # We have ping info
        if web["active"]:
            if hostTests["lastWeb"] + (web["intervalMinutes"] * 60) < time.time():
                hostTests["lastWeb"] = time.time()
                # We are due to run the web test
                if web["https"]:
                    target = "https://"
                else:
                    target = "http://"
                target += host["address"] + web["url"]
                webResult = uwebPage.webPage(target, web["match"], quiet=True)
                if webResult == None:
                    print("Web failed to ", target)
                else:
                    print("Web ", target, " rtl:", webResult[0], " match:",
                          webResult[1], " status:", webResult[2])
    # Update the last update times
    hosts.updateHostTests(hostTests)
    print(hosts.hostsTests)
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

    for loop in range(30):
        print("   * ", loop, " *")
        scheduler()

    print("")
    print("")
