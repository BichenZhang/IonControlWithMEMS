# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtWidgets
import PyQt5.uic

from externalParameter.persistence import DBPersist
from externalParameter.decimation import StaticDecimation
from modules.quantity import is_Q, Q
from functools import partial
import time
from collections import defaultdict
from .DACTableModel import DACTableModel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.GuiAppearance import restoreGuiState, saveGuiState 
import logging
from pulser.DAC import  DAC
from pulser.MEMSmirror import MEMSmirror

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/DDS.ui')
dacForm, dacBase = PyQt5.uic.loadUiType(uipath)

def extendTo(array, length, defaulttype):
    for _ in range( len(array), length ):
        array.append(defaulttype())
        
class DACUi(dacForm, dacBase):
    persistSpace = 'DAC'
    def __init__(self, DACClass, pulser, config, configName, globalDict, parent=None):
        self.isSetup = False
        dacBase.__init__(self, parent)
        dacForm.__init__(self)
        self.config = config
        self.dac = DACClass(pulser)
        self.DACClass = DACClass
        self.channelsConfigName = '{0}.dacExpressionChannels'.format(configName)
        self.autoApplyConfigName = '{0}.autoApply'.format(configName)
        self.guiStateConfigName = '{0}.guiState'.format(configName)
        self.dacChannels = self.config.get(self.channelsConfigName)
        self.dacChannels = None
        if not self.dacChannels or len(self.dacChannels)!=self.dac.numChannels:
            self.dacChannels = [DACClass.dacChannelSetting(globalDict=globalDict) for _ in range(self.dac.numChannels) ]
        for index, channel in enumerate(self.dacChannels):
            channel.globalDict = globalDict
            channel.onChange = partial(self.onChange, index)
        self.autoApply = self.config.get(self.autoApplyConfigName, True)
        self.decimation = defaultdict( lambda: StaticDecimation(Q(30, 's')))
        self.persistence = DBPersist()
        self.globalDict = globalDict
        self.pulser = pulser
        
    def setupUi(self, parent):
        dacForm.setupUi(self, parent)
        self.dacTableModel = DACTableModel(self.dacChannels, self.globalDict)
        self.tableView.setModel( self.dacTableModel )
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(2, self.delegate)
        self.applyButton.clicked.connect( self.onApply )
        self.resetButton.clicked.connect( self.onReset )
        self.writeAllButton.clicked.connect( self.onWriteAll )
        self.autoApplyBox.setChecked( self.autoApply )
        self.autoApplyBox.stateChanged.connect( self.onStateChanged )
        try:
            self.onWriteAll( writeUnchecked=True )
        except Exception as e:
            logging.getLogger(self.DACClass.__name__).warning( "Ignored error while setting dac or mems: {0}".format(e) )
        if self.DACClass != MEMSmirror:
            self.onApply()
        self.dacTableModel.voltageChanged.connect( self.onVoltage )
        self.dacTableModel.enableChanged.connect( self.onEnableChanged )
        restoreGuiState(self, self.config.get(self.guiStateConfigName))
        self.isSetup = True
            
    def onEnableChanged(self, channel, value):
        self.dac.setVoltage(channel, self.dacChannels[channel].outputVoltage )
            
    def setDisabled(self, disabled):
        pass
            
    def onStateChanged(self, state ):
        self.autoApply = self.autoApplyBox.isChecked()

    def onVoltage(self, channel, value):
        self.dac.setVoltage(channel, self.dacChannels[channel].outputVoltage, autoApply=self.autoApply )
        self.decimation[(0, channel)].decimate( time.time(), self.dacChannels[channel].outputVoltage, partial(self.persistCallback, "Voltage:{0}".format(self.dacChannels[channel].name if self.dacChannels[channel].name else channel)) )
        
    def persistCallback(self, source, data):
        time, value, minval, maxval = data
        unit = None
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
        self.persistence.persist(self.persistSpace, source, time, value, minval, maxval, unit)
    
    def onWriteAll(self, writeUnchecked=False):
            if len(self.dacChannels) > 0:
                with self.DACClass.combineWrites(self.dac) as stream:
                    for channel, settings in enumerate(self.dacChannels):
                        if writeUnchecked or settings.resetAfterPP:
                            stream.setVoltage(channel, settings.outputVoltage, autoApply=self.autoApply, applyAll=True)

    def saveConfig(self):
        self.config[self.channelsConfigName] = self.dacChannels
        self.config[self.autoApplyConfigName] = self.autoApply
        self.config[self.guiStateConfigName] = saveGuiState( self )
        
    def onApply(self):
        if self.dacChannels:
            if self.DACClass == DAC:
                self.dac.setVoltage(0, self.dacChannels[0].outputVoltage, autoApply=True, applyAll=True )
            else:
                self.onWriteAll()  # Apply is meaningless for MEMS unless we want to send an "update" message or pulse somewhere.
        
    def onReset(self):
        self.dac.reset(self.dac)

    def onChange(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.dacTableModel.setVoltage(self.dacTableModel.createIndex(index, 2), value)

    def evaluate(self, name):  # used on global variable update
        for channel, settings in enumerate(self.dacChannels):
            if settings.evaluateVoltage( self.globalDict ):
                self.dac.setVoltage(channel, settings.outputVoltage)
        if self.autoApply:
            self.onApply()
        self.tableView.viewport().repaint()

             
if __name__ == "__main__":
    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    with configshelve.configshelve("test") as config:
        ui = DACUi(config, None)
        ui.setupUi(ui)
        ui.show()
        sys.exit(app.exec_())
