#!/usr/bin/env python
# aeo_labs_mullti_5.py
# Copyright (C) ContinuumBridge Limited, 2014 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#
ModuleName               = "aeon_labs_multi_5"
BATTERY_CHECK_INTERVAL   = 600      # How often to check battery (secs)
SENSOR_POLL_INTERVAL     = 300      # How often to request sensor values

import sys
import time
import os
from pprint import pprint
import logging
from cbcommslib import CbAdaptor
from cbconfig import *
from twisted.internet import threads
from twisted.internet import reactor

class Adaptor(CbAdaptor):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.status =           "ok"
        self.state =            "stopped"
        self.apps =             {"binary_sensor": [],
                                 "temperature": [],
                                 "humidity": [],
                                 "luminance": []}
        # super's __init__ must be called:
        #super(Adaptor, self).__init__(argv)
        CbAdaptor.__init__(self, argv)
 
    def setState(self, action):
        # error is only ever set from the running state, so set back to running if error is cleared
        if action == "error":
            self.state == "error"
        elif action == "clear_error":
            self.state = "running"
        logging.debug("%s %s state = %s", ModuleName, self.id, self.state)
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def sendParameter(self, parameter, data, timeStamp):
        msg = {"id": self.id,
               "content": parameter,
               "data": data,
               "timeStamp": timeStamp}
        for a in self.apps[parameter]:
            self.sendMessage(msg, a)

    def checkBattery(self):
        cmd = {"id": self.id,
               "request": "post",
               "address": self.addr,
               "instance": "0",
               "commandClass": "128",
               "action": "Get",
               "value": ""
              }
        self.sendZwaveMessage(cmd)
        reactor.callLater(BATTERY_CHECK_INTERVAL, self.checkBattery)

    def pollSensors(self):
        cmd = {"id": self.id,
               "request": "post",
               "address": self.addr,
               "instance": "0",
               "commandClass": "49",
               "action": "Get",
               "value": ""
              }
        self.sendZwaveMessage(cmd)
        reactor.callLater(SENSOR_POLL_INTERVAL, self.pollSensors)

    def onZwaveMessage(self, message):
        #logging.debug("%s %s onZwaveMessage, message: %s", ModuleName, self.id, str(message))
        if message["content"] == "init":
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "48",
                   "value": "1"
                  }
            self.sendZwaveMessage(cmd)
            # Temperature
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "1"
                  }
            self.sendZwaveMessage(cmd)
            # luminance
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "3"
                  }
            self.sendZwaveMessage(cmd)
            # Humidity
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "5"
                  }
            self.sendZwaveMessage(cmd)
            # Battery
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "128"
                  }
            self.sendZwaveMessage(cmd)
            # 8 s timeout period of no-motion detected before the Multisensor sends the OFF state after being triggered.
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "3,8,2"
                  }
            self.sendZwaveMessage(cmd)
            reactor.callLater(60, self.checkBattery)
            reactor.callLater(30, self.pollSensors)
        elif message["content"] == "data":
            try:
                if message["commandClass"] == "49":
                    if message["data"]["name"] == "1":
                        temperature = message["data"]["val"]["value"] 
                        #logging.debug("%s %s onZwaveMessage, temperature: %s", ModuleName, self.id, str(temperature))
                        self.sendParameter("temperature", temperature, time.time())
                    elif message["data"]["name"] == "3":
                        luminance = message["data"]["val"]["value"] 
                        #logging.debug("%s %s onZwaveMessage, luminance: %s", ModuleName, self.id, str(luminance))
                        self.sendParameter("luminance", luminance, time.time())
                    elif message["data"]["name"] == "5":
                        humidity = message["data"]["val"]["value"] 
                        #logging.debug("%s %s onZwaveMessage, humidity: %s", ModuleName, self.id, str(humidity))
                        self.sendParameter("humidity", humidity, time.time())
                elif message["commandClass"] == "48":
                    if message["data"]["name"] == "1":
                        if message["data"]["level"]["value"]:
                            b = "on"
                        else:
                            b = "off"
                        logging.debug("%s %s onZwaveMessage, alarm: %s", ModuleName, self.id, b)
                        self.sendParameter("binary_sensor", b, time.time())
                elif message["commandClass"] == "128":
                     #logging.debug("%s %s onZwaveMessage, battery message: %s", ModuleName, self.id, str(message))
                     battery = message["data"]["last"]["value"] 
                     logging.info("%s %s battery level: %s", ModuleName, self.id, battery)
                     msg = {"id": self.id,
                            "status": "battery_level",
                            "battery_level": battery}
                     self.sendManagerMessage(msg)
            except:
                logging.warning("%s %s onZwaveMessage, unexpected message", ModuleName, str(message))

    def onAppInit(self, message):
        logging.debug("%s %s %s onAppInit, req = %s", ModuleName, self.id, self.friendly_name, message)
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "functions": [{"parameter": "binary_sensor", "interval": 0},
                              {"parameter": "temperature", "interval": 300},
                              {"parameter": "luminance", "interval": 300},
                              {"parameter": "humidity", "interval": 300}],
                "content": "functions"}
        self.sendMessage(resp, message["id"])
        self.setState("running")

    def onAppRequest(self, message):
        logging.debug("%s %s %s onAppRequest, message = %s", ModuleName, self.id, self.friendly_name, message)
        # Switch off anything that already exists for this app
        for a in self.apps:
            if message["id"] in self.apps[a]:
                self.apps[a].remove(message["id"])
        # Now update details based on the message
        for f in message["functions"]:
            if message["id"] not in self.apps[f["parameter"]]:
                self.apps[f["parameter"]].append(message["id"])
        logging.debug("%s %s %s apps: %s", ModuleName, self.id, self.friendly_name, str(self.apps))

    def onAppCommand(self, message):
        logging.debug("%s %s %s onAppCommand, req = %s", ModuleName, self.id, self.friendly_name, message)
        if "data" not in message:
            logging.warning("%s %s %s app message without data: %s", ModuleName, self.id, self.friendly_name, message)
        else:
            logging.warning("%s %s %s This is a sensor. Message not understood: %s", ModuleName, self.id, self.friendly_name, message)

    def onConfigureMessage(self, config):
        """Config is based on what apps are to be connected.
            May be called again if there is a new configuration, which
            could be because a new app has been added.
        """
        logging.debug("%s onConfigureMessage, config: %s", ModuleName, config)
        self.setState("starting")

if __name__ == '__main__':
    Adaptor(sys.argv)
