import json
import os
import time
import shared
import gc


class NetLogger:

    FILE_PREFIX = '/logger/'

    def __init__(self):
        if shared.hasSDCard:
            self.FILE_PREFIX = "/sd/logger/"

    def file_or_dir_exists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def getNDFileName(self, id, type):
        # return the file name to be used for todays netdata records for the host id
        now = time.localtime()
        NDFileName = self.FILE_PREFIX + \
            "nd{}{:0>2}{:0>2}{}{:0>3}.tab".format(
                now[0], now[1], now[2], type, id)
        return NDFileName

    def loggerLineBuilder(self, netLoggerRecord):
        loggerLine = ""
        print(netLoggerRecord)
        type = netLoggerRecord["type"]
        if type == "ping":
            if netLoggerRecord["success"]:
                loggerLine = "{}\t{}\n".format(
                    time.time(), netLoggerRecord["rtl"])
            else:
                loggerLine = "{}\t{}\n".format(time.time(), -1)
        if type == "bing":
            loggerLine = "{}\t{}\t{}\n".format(
                time.time(), netLoggerRecord["bps"], netLoggerRecord["rtl"])
        if type == "web":
            if netLoggerRecord["success"]:
                loggerLine = "{}\t{}\t{}\t{}\n".format(
                    time.time(), netLoggerRecord["ms"], netLoggerRecord["match"], netLoggerRecord["status"])
            else:
                loggerLine = "{}\t{}\t{}\t{}\n".format(
                    time.time(), -1, False, -1)
        print(loggerLine)
        return loggerLine

    def writeloggerRecord(self, netLoggerRecord):
        # Write a new network test results data record to
        # the appropriate netData file.

        if "id" not in netLoggerRecord:
            raise Exception("id missing from netLoggerRecord")
        if "type" not in netLoggerRecord:
            raise Exception("type missing from netLoggerRecord")
        if "success" not in netLoggerRecord:
            raise Exception("success missing from netLoggerRecord")
        if not (netLoggerRecord["type"] == "ping" or netLoggerRecord["type"] == "bing" or netLoggerRecord["type"] == "web"):
            raise Exception(
                "invalid netLoggerRecord type, must be ping, bing or web")
        loggerLine = self.loggerLineBuilder(netLoggerRecord)
        netDataLoggerFileName = self.getNDFileName(
            netLoggerRecord["id"], netLoggerRecord["type"])
        with open(netDataLoggerFileName, "a") as netDataLoggerFile:
            netDataLoggerFile.write(loggerLine)

    def getHistory(self, startTimestamp, id, type):
        # summarize based on hours of data selected
        # 12 hours no summary
        # 12-72 hours do hourly summary
        # >72 hours do daily summary

        # by default report on rtl for ping, bps for bing and ms for web

        gc.collect()

        entries = []
        valueTotal = 0
        valueCount = 0
        lastSummaryTime = 0

        begin = startTimestamp
        end = time.time()

        hoursHistory = (end-begin)/(60*60)
        summaryType = "X"  # x = no summary
        if hoursHistory > 12 and hoursHistory < 72:
            summaryType = "H"
        if hoursHistory > 72:
            summaryType = "D"

        startOfBeginDay = begin - \
            (time.localtime(begin)[3] * 60 * 60) - \
            (time.localtime(begin)[4] * 60) + 1
        for fileDate in range(startOfBeginDay, end, (60*60*24)):
            localFileDate = time.localtime(fileDate)
            logName = self.FILE_PREFIX + "nd{}{:0>2}{:0>2}{}{:0>3}.tab".format(
                localFileDate[0], localFileDate[1], localFileDate[2], type, id)
            print("getHistory logName:", logName, localFileDate)
            if self.file_or_dir_exists(logName):
                with open(logName, "r") as loggingFile:
                    # filter out entries that are not in required range
                    loggingFileLines = loggingFile.readlines()
                    for line in loggingFileLines:
                        lineValues = line.split("\t")
                        print(begin, end, int(
                            lineValues[0]), int(lineValues[1]))
                        if int(lineValues[0]) >= begin and int(lineValues[0]) <= end:
                            if summaryType == "X":
                                # Build dictionary item for current hour
                                entries.append(
                                    {"timeStamp": int(lineValues[0]), "value": int(lineValues[1])})
                            else:
                                # Summarize data
                                valueTotal += int(lineValues[1])
                                hoursTotal += 1
                        if lastSummaryTime != 0:
                            timestamp = int(lineValues[0])
                            if (summaryType == "H" and (timestamp - lastSummaryTime) > 60*60) \
                                    or (summaryType == "D" and (timestamp - lastSummaryTime) > 60*60*24):
                                # Add a summary entry
                                if valueCount > 0:
                                    entries.append(
                                        {"timeStamp":  lastSummaryTime, "value": valueTotal/valueCount})
                                valueCount = 0
                                valueTotal = 0
                                # Calculate the start of the next summary time
                                if summaryType == "H":
                                    # set to beginning or the hour
                                    hourBegin = timestamp - \
                                        (time.localtime(timestamp)[3] * 60 * 60) - \
                                        (time.localtime(timestamp)[4] * 60) - \
                                        time.localtime(timestamp)[5] + 1
                                    lastSummaryTime = hourBegin
                                else:
                                    # set to beginning or the day
                                    dayBegin = timestamp - \
                                        (time.localtime(timestamp)[3] * 60 * 60) - \
                                        (time.localtime(timestamp)[4] * 60) + 1
                                    lastSummaryTime = dayBegin

        # print("entries:", entries)
        return entries
