#!/usr/bin/env python
# aeo_labs_mullti_5.py
# Copyright (C) ContinuumBridge Limited, 2014 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#
ModuleName               = "aeon_labs_multi_5"
BATTERY_CHECK_INTERVAL   = 300      # How often to check battery (secs)
SENSOR_POLL_INTERVAL     = 180      # How often to request sensor values

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
                                 "luminescence": []}
        # super's __init__ must be called:
        #super(Adaptor, self).__init__(argv)
        CbAdaptor.__init__(self, argv)
 
    def setState(self, action):
        if self.state == "stopped":
            if action == "starting":
                self.state = "starting"
        elif self.state == "starting":
            if action == "inUse":
                self.state = "activate"
        if self.state == "activate":
            reactor.callLater(0, self.poll)
            self.state = "running"
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

    def reportState(self, state):
        logging.debug("%s %s Switch state = %s", ModuleName, self.id, state)
        msg = {"id": self.id,
               "timeStamp": time.time(),
               "content": "switch_state",
               "data": state}
        for a in self.apps:
            self.sendMessage(msg, a)

    def sendParameter(self, parameter, data, timeStamp):
        msg = {"id": self.id,
               "content": parameter,
               "data": data,
               "timeStamp": timeStamp}
        for a in self.apps[parameter]:
            self.sendMessage(msg, a)

    def onStop(self):
        # Mainly caters for situation where adaptor is told to stop while it is starting
        pass

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

    def onOff(self, boolean):
        if boolean:
            return "on"
        elif not boolean:
            return "off"

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
            # Luminescence
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
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "128",
                   "value": "1"
                  }
            self.sendZwaveMessage(cmd)
            reactor.callLater(20, self.checkBattery)
            reactor.callLater(30, self.pollSensors)
        elif message["content"] == "data":
            #try:
            if True:
                if message["commandClass"] == "49":
                    if message["data"]["name"] == "1":
                        temperature = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, temperature: %s", ModuleName, self.id, str(temperature))
                        self.sendParameter("temperature", temperature, time.time())
                    elif message["data"]["name"] == "3":
                        luminescence = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, luminescence: %s", ModuleName, self.id, str(luminescence))
                        self.sendParameter("luminescence", luminescence, time.time())
                    elif message["data"]["name"] == "5":
                        humidity = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, humidity: %s", ModuleName, self.id, str(humidity))
                        self.sendParameter("humidity", humidity, time.time())
                elif message["commandClass"] == "48":
                    if message["data"]["name"] == "1":
                        triggered = message["data"]["level"]["value"] 
                        logging.debug("%s %s onZwaveMessage, triggered: %s", ModuleName, self.id, str(triggered))
            #except:
            #    logging.debug("%s %s onZwaveMessage, no data-val-value", ModuleName, self.id)

    def onAppInit(self, message):
        logging.debug("%s %s %s onAppInit, req = %s", ModuleName, self.id, self.friendly_name, message)
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "functions": [{"parameter": "binary_sensor"},
                              {"parameter": "temperature"},
                              {"parameter": "luminescence"},
                              {"parameter": "humidity"}],
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
    adaptor = Adaptor(sys.argv)
