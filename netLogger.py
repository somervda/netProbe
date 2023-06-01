import json
import os
import time
import shared


# netLoggerRecord formate should be
# { "id":<hostId>,"type":<ping|bing|wan>: ....test result data...}


class NetLogger:

    FILE_PREFIX  = '/'
    def __init__(self):
        if shared.hasSDCard:
            self.FILE_PREFIX = "/sd/" 

    def file_or_dir_exists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
        
    def getNDFileName(self,id):
        # return the file name to be used for todays netdata records for the host id
        now = time.localtime()
        print(now)
        NDFileName= self.FILE_PREFIX + "{}{}{}-{}".format(now[0], now[1], now[2], id)
        # NDFileName = self.FILE_PREFIX + str(now[0]) + str(now[1] + str(now[2]) + "-" + str(id))
        return NDFileName

    def write(self,netLoggerRecord):
        # Write a new network test results data record to 
        # the appropriate netData file.

        netDataFileName = "nd"
        # if not self.file_or_dir_exists(self.CONFIG_FILE):
        #     raise Exception("File required: " + self.CONFIG_FILE)

        # with open(self.CONFIG_FILE, "r") as configFile: