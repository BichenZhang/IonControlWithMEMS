# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui
import PyQt5.uic

from externalParameter.persistence import DBPersist
from externalParameter.decimation import StaticDecimation
from modules.quantity import is_Q, Q
from functools import partial
import time
from collections import defaultdict
from modules.Expression import Expression
from .MemsPositionsTableModel import MemsPositionsTableModel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.GuiAppearance import restoreGuiState, saveGuiState 
import logging
from modules.Utility import unique
from pulser.PulserConfig import DAADInfo
from pulser.MemsPositions import MemsPositions

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/MemsPositions.ui')
MemsPositionsForm, MemsPositionsBase = PyQt5.uic.loadUiType(uipath)

def extendTo(array, length, defaulttype):
    for _ in range( len(array), length ):
        array.append(defaulttype())
        
        
class MemsPositionSettings(object):
    expression = Expression()
    def __init__(self):
        self.x1 = Q(0, 'V')
        self.x1c = Q(0, 'V')
        self.y1 = Q(0, 'V')
        self.y1c = Q(0, 'V')
        self.x2 = Q(0, 'V')
        self.x2c = Q(0, 'V')
        self.y2 = Q(0, 'V')
        self.y2c = Q(0, 'V')
        self.x1Text = None
        self.x1cText = None
        self.y1Text = None
        self.y1cText = None
        self.x2Text = None
        self.x2cText = None
        self.y2Text = None
        self.y2cText = None

        self.ion = None #was channel
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('ion', None)

class Settings:
    pass

class MemsPositionsUi(MemsPositionsForm, MemsPositionsBase):
    def __init__(self, pulser, config, configName='MemsPositionsUi', globalDict=dict(), parent=None):
        self.persistSpace = 'MEMSPositions'
        MemsPositionsBase.__init__(self, parent)
        MemsPositionsForm.__init__(self)

        self.config = config
        self.memsPositions = MemsPositions(pulser)
        self.channelsConfigName = '{0}.memsPositionsExpressionConfigName'.format(configName)
        self.guiStateConfigName = '{0}.guiState'.format(configName)
        self.memsPositionsChannels = self.config.get(self.channelsConfigName)
        if not self.memsPositionsChannels or len(self.memsPositionsChannels) != self.memsPositions.numIons:
            self.memsPositionsChannels = [MemsPositions.memsPositionsSetting(globalDict=globalDict) for _ in range(self.memsPositions.numIons)]
        for index, channel in enumerate(self.memsPositionsChannels):
            channel.globalDict = globalDict
            channel.onChange = partial(self.onChange, index)
        self.decimation = defaultdict(lambda: StaticDecimation(Q(30, 's')))
        self.persistence = DBPersist()
        self.globalDict = globalDict
        self.pulser = pulser


    def setupUi(self, parent):
        MemsPositionsForm.setupUi(self, parent)
        self.MemsPositionsTableModel = MemsPositionsTableModel(self.memsPositions, self.globalDict)
        self.tableView.setModel( self.MemsPositionsTableModel )
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(0, self.delegate)
        self.tableView.setItemDelegateForColumn(1, self.delegate)
        self.tableView.setItemDelegateForColumn(2, self.delegate)
        self.tableView.setItemDelegateForColumn(3, self.delegate)
        self.tableView.setItemDelegateForColumn(4, self.delegate)
        self.tableView.setItemDelegateForColumn(5, self.delegate)
        self.tableView.setItemDelegateForColumn(6, self.delegate)
        self.tableView.setItemDelegateForColumn(7, self.delegate)

        self.accepted.connect( self.onOk )
        self.rejected.connect( self.onCancel )

        if hasattr(self.settings, 'state'):
            self.restoreState( self.settings.state )
        restoreGuiState(self, self.config.get(self.guiStateConfigName))

    def onChange(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, 2), value)

    def evaluate(self, name):  # used on global variable update
        for channel, settings in enumerate(self.memsPositionsChannels):
            if settings.evaluateVoltage( self.globalDict ):
                self.memsPositions.setVoltage(channel, settings.outputVoltage)
        self.tableView.viewport().repaint()

    def persistCallback(self, source, data):
        time, value, minval, maxval = data
        unit = None
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
        self.persistence.persist(self.persistSpace, source, time, value, minval, maxval, unit)

    def saveConfig(self):
        self.config[self.channelsConfigName] = self.memsPositionsChannels
        self.settings.isVisible = self.isVisible()
        self.config[self.configname] = self.settings
        self.config[self.guiStateConfigName] = saveGuiState(self)
        
    def onOk(self):
        self.saveConfig()
        # update globals
        ## Save all values to globals.
        # ionObj = self.memsions[ion]
        # ion = ionObj.ion
        # self.decimation[(0, ion)].decimate(time.time(), value, partial(self.persistCallback, "Frequency:{0}".format(
        #     ionObj.name if ionObj.name else ion)))

    def onCancel(self):
        pass
        # close window (don't save values)

    def closeEvent(self, e):
        self.onCancel()

    # def evaluate(self, name):
    #     for setting in self.memsions:
    #         if setting.evaluateFrequency( self.globalDict ):
    #             self.ad9912.setFrequency(setting.ion, setting.frequency)
    #         if setting.evaluatePhase( self.globalDict ):
    #             self.ad9912.setPhase(setting.ion, setting.phase)
    #         if setting.evaluateAmplitude( self.globalDict ):
    #             self.ad9912.setAmplitude(setting.ion, setting.amplitude)
    #     if self.autoApply:
    #         self.onApply()
    #     self.tableView.viewport().repaint()
             
if __name__ == "__main__":
    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    with configshelve.configshelve("test") as config:
        ui = memsUi(config, None)
        ui.setupUi(ui)
        ui.show()
        sys.exit(app.exec_())
