import os
import time
import io
import sys
import shared


class AppLogger:
    APPLOGFILE = "/applog.txt"

    def __init__(self):
        if shared.hasSDCard:
            self.APPLOGFILE = "/sd" + self.APPLOGFILE

    def getFileName(self):
        return self.APPLOGFILE

    def getTimeStamp(self):
        formatedTime = ""
        now = time.localtime()
        formatedTime = "{}-{}-{} {}:{}:{}".format(
            now[0], now[1], now[2], now[3], now[4], now[5])
        return formatedTime

    def writeLogLine(self, logLine):
        with open(self.APPLOGFILE, "a") as logFile:
            logFile.write(self.getTimeStamp() + " " +
                          logLine.replace("\n", "\t") + "\n")

    def writeException(self, e):
        # Write appLog record using application exception object
        s = io.StringIO()
        sys.print_exception(e, s)
        self.writeLogLine(s.getvalue())

    def printException(self, e):
        # Print application exception object
        s = io.StringIO()
        sys.print_exception(e, s)
        print(s.getvalue())

    def getLog(self):
        with open(self.APPLOGFILE, "r") as logFile:
            return logFile.read().replace("\n", "<br>")

    def clearLog(self):
        with open(self.APPLOGFILE, "w") as logFile:
            logFile.write("")
