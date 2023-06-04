import os
import time
import io
import sys
import shared


APPLOGFILE = "applog.txt"


class AppLogger:
    def __init__(self):
        if shared.hasSDCard:
            self.APPLOGFILE = "/sd" + self.APPLOGFILE

    def getTimeStamp(self):
        formatedTime = ""
        now = time.localtime()
        formatedTime = "{}-{}-{} {}:{}:{}".format(
            now[0], now[1], now[2], now[3], now[4], now[5])
        return formatedTime

    def writeLogLine(self, logLine):
        with open(APPLOGFILE, "a") as logFile:
            logFile.write(self.getTimeStamp() + " " +
                          logLine.replace("\n", "\t") + "\n")

    def writeException(self, e):
        # Write appLog record using application exception object
        s = io.StringIO()
        sys.print_exception(e, s)
        self.writeLogLine(s.getvalue())

    def getLog(self):
        with open(APPLOGFILE, "r") as logFile:
            return logFile.read().replace("\n", "<br>")

    def clearLog(self):
        with open(APPLOGFILE, "w") as logFile:
            logFile.write("")
