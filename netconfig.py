import json
import os
import errno


class NetConfig:
    CONFIG_FILE = "netconfig.json"
    useWiFi: bool
    IP = ""
    gateway = ""
    dns = ""
    netmask = ""
    wifiSSID = ""
    wifiPassword = ""
    ntp = ""
    dhcp: bool

    def __init__(self):
        self.getConfig()

    def file_or_dir_exists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def getConfig(self):
        if not self.file_or_dir_exists(self.CONFIG_FILE):
            raise Exception("File required: " + self.CONFIG_FILE)

        with open(self.CONFIG_FILE, "r") as configFile:
            network = json.loads(configFile.read())
            if "wifiSSID" in network:
                self.wifiSSID = network["wifiSSID"]
            if "wifiPassword" in network:
                self.wifiPassword = network["wifiPassword"]
            if "useWiFi" in network:
                self.useWiFi = network["useWiFi"]
                if not type(self.useWiFi) is bool:
                    raise Exception(
                        "useWifi must be boolean in netconfig.json")
                if self.wifiPassword == "" or self.wifiSSID == "":
                    raise Exception(
                        "Missing wifiSSID or wifiPassword settings in netconfig.json")
            else:
                raise Exception("Missing useWifi setting in netconfig.json")
            if "IP" in network:
                self.IP = network["IP"]
            if "gateway" in network:
                self.gateway = network["gateway"]
            if "dns" in network:
                self.dns = network["dns"]
            if "netmask" in network:
                self.netmask = network["netmask"]
            if "ntp" in network:
                self.ntp = network["ntp"]
            if "dhcp" in network:
                self.dhcp = network["dhcp"]
                if not type(self.dhcp) is bool:
                    raise Exception("dhcp must be boolean in netconfig.json")
                if not self.dhcp:
                    if self.IP == "" or self.gateway == "" or self.dns == "" or self.netmask == "":
                        raise Exception(
                            "Missing IP,gateway,dns,or netmask from netconfig.json for non dhcp connection")
            else:
                raise Exception("Missing dhcp setting in netconfig.json")
