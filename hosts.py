import json
import os
import shared


class Hosts:
    # hosts data
    HOSTS_FILE = "/hosts.json"
    hosts = any
    maxId = 0
    # host scheduling
    lastHostTested = 0
    hostTests = []

    def __init__(self):
        if shared.hasSDCard:
            self.HOSTS_FILE = "/sd" + self.HOSTS_FILE
        self.getHosts()
        self.buildHostTests()

    def file_or_dir_exists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def setMaxId(self):
        # Find the maximum id
        self.maxId = 0
        for host in self.hosts:
            if host["id"] > self.maxId:
                self.maxId = host["id"]

    def buildHostTests(self):
        # Build a new host tests array based on hosts data
        self.hostsTests = []
        for host in self.hosts:
            hostTests = {"id": host["id"],
                         "lastPing": 0, "lastBing": 0, "lastWeb": 0}
            self.hostsTests.append(hostTests)

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

    def getHostTests(self, id):
        for hostTests in self.hostsTests:
            if hostTests["id"] == id:
                return(hostTests)
        return {}

    def updateHost(self, updatedHost):
        # Updated a host based on the updated host's id
        for host in self.hosts:
            if host["id"] == updatedHost["id"]:
                self.hosts.remove(host)
                self.hosts.append(updatedHost)
                self.setMaxId()
                self.writeHosts()

    def updateHostTests(self, updatedHostTests):
        # Updated a hostTests based on the updated host's id
        for hostTests in self.hostsTests:
            if hostTests["id"] == updatedHostTests["id"]:
                self.hostsTests.remove(hostTests)
                self.hostsTests.append(updatedHostTests)

    def getId(self,obj):
        return obj["id"]

    def findNextHostToTest(self):
        self.hostsTests.sort(key=self.getId)
        nextFound=False
        for hostTests in self.hostsTests:
            if hostTests["id"] > self.lastHostTested:
                nextFound=True
                self.lastHostTested=hostTests["id"]
                break
        if not nextFound:
            for hostTests in self.hostsTests:
                if hostTests["id"] > 0:
                    nextFound=True
                    self.lastHostTested=hostTests["id"] 
                    break
        if not nextFound:
            # Not really needed
            self.lastHostTested=0



    def removeHost(self, id):
        for host in self.hosts:
            if host["id"] == id:
                self.hosts.remove(host)
                self.setMaxId()
                self.writeHosts()
        # Also update hostsTests
        for hostTests in self.hostsTests:
            if hostTests["id"] == id:
                self.hostsTests.remove(hostTests)

    def addHost(self, host):
        host["id"] = self.maxId + 1
        self.hosts.append(host)
        self.setMaxId()
        self.writeHosts()
        # Also update hostsTests
        self.hostsTests.append(
            {"id": self.maxId, "lastPing": 0, "lastBing": 0, "lastWeb": 0})

    def writeHosts(self):
        with open(self.HOSTS_FILE, "w") as hostsFile:
            hostsFile.write(json.dumps(self.hosts))
