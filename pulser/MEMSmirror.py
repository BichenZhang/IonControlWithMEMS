# -*- coding: utf-8 -*-
"""
Created on Tue Feb 19 14:53:26 2013

@author: plmaunz
"""

import logging
import math
import struct

from pulser.PulserHardwareClient import check
from modules.magnitude import mg

class MEMSException(Exception):
    pass

class MEMSmirror:
    def __init__(self, pulser):
        self.pulser = pulser

    def setVoltage(self, channel, mirror, voltage):
        intVoltage = int( & 0xffffffffffff
        self.sendCommand(channel, 0, intVoltage)
        return intFrequency

    def sendCommand(self, channel, cmd, data):
        if self.pulser:
            #ALL THIS TO BE UPDATED YET!!!!
            check( self.pulser.SetWireInValue(0x03, (channel & 0xff)<<4 | (cmd & 0xf) ), "MEMS" )
            self.pulser.setExtendedWireIn(0x12, data)
            self.pulser.UpdateWireIns()
            check( self.pulser.ActivateTriggerIn(0x40, ?), "MEMS trigger")
            self.pulser.UpdateWireIns()
        else:
            logging.getLogger(__name__).warning( "Pulser not available" )

        
if __name__ == "__main__":
    import modules.magnitude as magnitude
    
    mems = MEMSmirror(None)
    mems.setVoltage(channel, 1, magnitude.mg(1, 'V'))
    