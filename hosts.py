import json
import os
import shared


class Hosts:

    HOSTS_FILE = "/hosts.json"
    hosts = any
    maxId = 0

    def __init__(self):
        if shared.hasSDCard:
            self.HOSTS_FILE = "/sd" + self.HOSTS_FILE
        self.getHosts()

    def file_or_dir_exists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
        
    def setMaxId(self):
        # Find the maximum id
        for host in self.hosts:
            if host["id"] > self.maxId:
                self.maxId = host["id"]

    def getHosts(self):
        if not self.file_or_dir_exists(self.HOSTS_FILE):
            raise Exception("File required: " + self.HOSTS_FILE)

        with open(self.HOSTS_FILE, "r") as hostsFile:
            self.hosts = json.loads(hostsFile.read())
            self.setMaxId()


    def getHost(self, id):
        for host in self.hosts:
            if host["id"] == id:
                return(host)
        return {}

    def updateHost(self, newHost):
        for host in self.hosts:
            if host["id"] == newHost["id"]:
                self.hosts.remove(host)
                self.hosts.append(newHost)
                self.setMaxId()
                self.writeHosts()


    def removeHost(self, id):
        for host in self.hosts:
            if host["id"] == id:
                self.hosts.remove(host)
                self.setMaxId()
                self.writeHosts()


    def addHost(self, host):
        host["id"] = self.maxId + 1
        self.hosts.append(host)
        self.setMaxId()
        self.writeHosts()


    def writeHosts(self):
        with open(self.HOSTS_FILE, "w") as hostsFile:
            hostsFile.write(json.dumps(self.hosts))
