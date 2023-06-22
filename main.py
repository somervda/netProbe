from microdot_asyncio import Microdot,  send_file
import uasyncio
import uwebPage
from microdot_cors import CORS
import shared
import gc
import os
import time
import uping
import ubing
import network
import machine
import ntptime
# import micropython


from appLogger import AppLogger
from netLogger import NetLogger
from hosts import Hosts
from netconfig import NetConfig

hosts: Hosts
netLogger: NetLogger

app = Microdot()
CORS(app, allowed_origins="*", allow_credentials=True)
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


async def scheduler(quiet=True):
    global hosts
    global netLogger
    global skipTestTimestamp
    lastSleepTime = time.time()
    await uasyncio.sleep(0.1)
    # Perform scheduling of tests on next host
    while True:
        if skipTestTimestamp < time.time():
            gc.collect()
            nextHostToTest = hosts.findNextHostToTest()
            host = hosts.getHost(nextHostToTest)
            not quiet and print(
                host["address"], "   mem_free:", gc.mem_free(), end="")
            hostTests = hosts.getHostTests(nextHostToTest)
            if "ping" in host:
                not quiet and print(".", end="")
                ping = host["ping"]
                hostTests["pingActive"] = ping["active"]
                # We have ping info
                if ping["active"]:
                    if hostTests["lastPing"] + (ping["intervalMinutes"] * 60) < time.time():
                        hostTests["lastPing"] = time.time()
                        # We are due to run the ping test
                        pingResult = uping.ping(host["address"], size=16)
                        if pingResult == None:
                            hostTests["pingSuccess"] = False
                            # Leave last good pingRTL in table
                            netLoggerRecord = {
                                "id": host["id"], "type": "ping",  "success": False}
                        else:
                            hostTests["pingSuccess"] = True
                            hostTests["pingRTL"] = int(pingResult[0])
                            netLoggerRecord = {
                                "id": host["id"], "type": "ping", "rtl": int(pingResult[0]), "success": True}
                        netLogger.writeloggerRecord(netLoggerRecord)
            # print("mem_free", gc.mem_free())
            if "bing" in host:
                not quiet and print(".", end="")
                bing = host["bing"]
                hostTests["bingActive"] = bing["active"]
                # We have ping info
                if bing["active"]:
                    if hostTests["lastBing"] + (bing["intervalMinutes"] * 60) < time.time():
                        hostTests["lastBing"] = time.time()
                        # We are due to run the bing test (Reducing samples and timeout to speed it up)
                        bingResult = await ubing.bing(
                            host["address"], maxSize=1400)
                        if bingResult[0] == -1:
                            hostTests["bingSuccess"] = False
                            netLoggerRecord = {
                                "id": host["id"], "type": "bing", "bps": bingResult[0], "rtl":  int(bingResult[1]),  "success": False}
                        else:
                            hostTests["bingSuccess"] = True
                            hostTests["bingBPS"] = int(bingResult[0])
                            hostTests["bingRTL"] = int(bingResult[1])
                            netLoggerRecord = {
                                "id": host["id"], "type": "bing", "bps": bingResult[0], "rtl":  int(bingResult[1]),  "success": True}
                        netLogger.writeloggerRecord(netLoggerRecord)
            if "web" in host:
                not quiet and print(".", end="")
                web = host["web"]
                hostTests["webActive"] = web["active"]
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
                                hostTests["webSuccess"] = False
                                netLoggerRecord = {
                                    "id": host["id"], "type": "web",  "success": False}
                            else:
                                hostTests["webSuccess"] = True
                                hostTests["webMS"] = int(webResult[0])
                                hostTests["webMatch"] = webResult[1]
                                netLoggerRecord = {"id": host["id"], "type": "web", "ms": int(webResult[0]),
                                                   "match": webResult[1], "status": webResult[2], "success": True}
                            netLogger.writeloggerRecord(netLoggerRecord)
            # Update the last update times
            hosts.updateHostTests(hostTests)
        not quiet and print("")

        # if time.localtime(lastSleepTime)[2] != time.localtime()[2]:
        #     # Its a new day - reboot (Keep heap happy!)
        #     machine.reset()
        # lastSleepTime = time.time()
        await uasyncio.sleep(10)

# MicroDot Web Services

# Get hosts and test info
@app.route('/hostStatus')
def getHostStatus(request):
    return hosts.getHostStatus(), 200


@app.route('/systemStatus')
def getSystemStatus(request):
    systemStatus = {}
    gc.collect()
    systemStatus["gc-free"] = gc.mem_free()
    # micropython.mem_info(1)
    systemStatus["hasSDCard"] = shared.hasSDCard
    statvfs = os.statvfs("/")
    systemStatus["InternalFreeSpace"] = statvfs[0] * statvfs[3]
    if shared.hasSDCard:
        statvfssd = os.statvfs("/sd")
        systemStatus["SdFreeSpace"] = statvfssd[0] * statvfssd[3]
    return systemStatus

# Get history
@app.route('/history/<start>/<id>/<type>')
def getHistory(request, start, id, type):
    # netLogger = NetLogger()
    gc.collect()
    return netLogger.getHistory(int(start), int(id), type), 200

# Get host
@app.route('/host/<id>')
def getHost(request, id):
    # netLogger = NetLogger()
    gc.collect()
    return hosts.getHost(int(id))

# Add host
@app.post('/host/add')
def addHost(request):
    gc.collect()
    print('/host/add', request.body)
    newHostId = hosts.addHost(request.json)
    return str(newHostId), 200

# Update host
@app.post('/host/update')
def updateHost(request):
    gc.collect()
    print('/host/update', request.body)
    updatedHostId = hosts.updateHost(request.json)
    return str(updatedHostId), 200

# Delete Host
@app.delete('/host/<id>')
def deleteHost(request, id):
    gc.collect()
    print('/host/delete', id)
    deletedHostId = hosts.deleteHost(id)
    return str(deletedHostId), 200

# Get list of errors
@app.route('/log')
def getSysLog(request):
    appLogger = AppLogger()
    return appLogger.getLog(), 200,  {'Content-Type': 'text/html'}


@app.route('/log/clear')
def clearSysLog(request):
    appLogger = AppLogger()
    appLogger.clearLog()
    return "", 200,  {'Content-Type': 'text/html'}


@app.before_request
def func(request):
    global skipTestTimestamp
    # Stop tests for seconds if someone is using the web interface
    skipTestTimestamp = time.time() + 10
    print("skipTestTimestamp", skipTestTimestamp)


@app.after_request
def func(request, response):
    # ...
    print("after_request")
    response.headers.update({"Access-Control-Allow-Origin": "*"})
    return response

#  All other request return static files from garden_ui folder
@app.route('/')
def index(request):
    return send_file('net-probe-ui/index.html')


@app.route('/<path:path>')
def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        # print("directory traversal is not allowed " + path)
        return 'Not found', 404
    # print(path)
    return send_file('net-probe-ui/' + path)


if __name__ == '__main__':
    # Check if we have a SD card plugged in
    gc.collect()
    time.sleep(1)
    # micropython.mem_info()

    try:
        sd = machine.SDCard(slot=1, width=1, sck=machine.Pin(
            14), miso=machine.Pin(2), mosi=machine.Pin(15))
        os.mount(sd, '/sd')
    except OSError:
        shared.hasSDCard = False
    appLogger = AppLogger()

    try:
        connect()
        print(net_if.ifconfig())
    except Exception as e:
        appLogger.writeException(e)
        print("Connect exception, restarting in 5 seconds...")
        time.sleep(5)
        machine.reset()
    appLogger.writeLogLine("*** Restart ***")

    hosts = Hosts()
    netLogger = NetLogger()
    # Fire up background co-routine first
    uasyncio.create_task(scheduler(quiet=False))
    try:
        # Fire up the microDot server (also runs as a background coroutine)
        # Note: debug requires a terminal connection so turn of when running in garden from battery
        app.run(debug=True, port=80)
    except:
        appLogger.writeLogLine("microDot Exception")
        print("Microdot exception, restarting in 5 seconds...")
        time.sleep(5)
        machine.reset()
