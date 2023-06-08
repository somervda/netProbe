from microdot_asyncio import Microdot,  send_file
import uasyncio
import uwebPage
import shared
import gc
import os
import time
import uping
import ubing
import network
import machine
import ntptime
import micropython

from appLogger import AppLogger
from netLogger import NetLogger
from hosts import Hosts
from netconfig import NetConfig

hosts: Hosts
netLogger: NetLogger

app = Microdot()
# If we start seeing web service activity then this gets set to a minute into the future
# and no network testing is performed until the time is in the past. This should make the
# web site more responsive
skipTestTimestamp = 0


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


async def scheduler():
    global hosts
    global netLogger
    global skipTestTimestamp
    # Perform scheduling of tests on next host
    while True:
        if skipTestTimestamp < time.time():
            nextHostToTest = hosts.findNextHostToTest()
            host = hosts.getHost(nextHostToTest)
            print(host["address"])
            print("mem_info", micropython.mem_info())
            gc.collect()
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
            print("mem_free", gc.mem_free())
            if "bing" in host:
                bing = host["bing"]
                # We have ping info
                if bing["active"]:
                    if hostTests["lastBing"] + (bing["intervalMinutes"] * 60) < time.time():
                        hostTests["lastBing"] = time.time()
                        # We are due to run the bing test (Reducing samples and timeout to speed it up)
                        bingtimer = time.time()
                        bingResult = ubing.bing(
                            host["address"], maxSize=1400, quiet=True)
                        print("bing duration:", time.time()-bingtimer)
                        if bingResult[0] == -1:
                            netLoggerRecord = {
                                "id": host["id"], "type": "bing", "bps": bingResult[0], "rtl":  int(bingResult[1]),  "success": False}
                        else:
                            netLoggerRecord = {
                                "id": host["id"], "type": "bing", "bps": bingResult[0], "rtl":  int(bingResult[1]),  "success": True}
                        netLogger.writeloggerRecord(netLoggerRecord)
            print("mem_free", gc.mem_free())
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
        # sleep for 20 seconds
        await uasyncio.sleep(20)

# MicroDot Web Services

# Get history
@app.route('/history/<start>/<id>/<type>')
def getHistory(request, start, id, type):
    netLogger = NetLogger()
    return netLogger.getHistory(int(start), int(id), type), 200,  {'Access-Control-Allow-Origin': '*'}

# Get list of errors
@app.route('/log')
def getSysLog(request):
    appLogger = AppLogger()
    return appLogger.getLog(), 200,  {'Access-Control-Allow-Origin': '*', 'Content-Type': 'text/html'}


@app.route('/log/clear')
def clearSysLog(request):
    appLogger = AppLogger()
    appLogger.clearLog()
    return "", 200,  {'Access-Control-Allow-Origin': '*', 'Content-Type': 'text/html'}


@app.before_request
def func(request):
    global skipTestTimestamp
    # Stop tests for seconds if someone is using the web interface
    skipTestTimestamp = time.time() + 60
    print("skipTestTimestamp", skipTestTimestamp)


if __name__ == '__main__':
    # Check if we have a SD card plugged in
    gc.collect()
    time.sleep(1)
    micropython.mem_info()

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

    appLogger = AppLogger()
    appLogger.writeLogLine("*** Restart ***")
    # Fire up background co-routine first
    uasyncio.create_task(scheduler())
    try:
        # Fire up the microDot server (also runs as a background coroutine)
        # Note: debug requires a terminal connection so turn of when running in garden from battery
        app.run(debug=True, port=80)
    except:
        appLogger.writeLogLine("microDot Exception")
        print("Microdot exception, restarting in 5 seconds...")
        time.sleep(5)
        machine.reset()
