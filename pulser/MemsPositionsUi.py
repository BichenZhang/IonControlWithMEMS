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

    def evaluateFrequency(self, globalDict ):
        if self.frequencyText:
            oldfreq = self.frequency
            self.frequency = self.expression.evaluateAsMagnitude(self.frequencyText, globalDict)
            return self.frequency!=oldfreq
        return False


class MemsPositionsUi(MemsPositionsForm, MemsPositionsBase):
    def __init__(self, pulser, config, configName='MemsPositionsUi', globalDict=dict(), parent=None):
        MemsPositionsBase.__init__(self, parent)
        MemsPositionsForm.__init__(self)
        if pulser.pulserConfiguration():
            self.ionInfo = sorted(list(pulser.pulserConfiguration().memsions.values()), key=lambda x: x.ion)
        else:
            self.ionInfo = []
        self.numions = len(self.ionInfo)
        self.config = config
        self.ionConfigName = '{0}.memsions'.format(configName)
        # self.autoApplyConfigName = '{0}.autoApply'.format(configName)
        self.guiStateConfigName = '{0}.guiState'.format(configName)
        oldmemsions = self.config.get(self.ionConfigName, [])
        self.memsions = [oldmemsions[i] if i < len(oldmemsions) else memsionSettings() for i in range(self.numions)]
        # self.autoApply = self.config.get(self.autoApplyConfigName, True)
        self.decimation = defaultdict(lambda: StaticDecimation(Q(30, 's')))
        self.persistence = DBPersist()
        self.globalDict = globalDict
        self.pulser = pulser
        self.persistSpace = 'MEMS'
        for index, ioninfo in enumerate(self.ionInfo):
            self.memsions[index].ion = ioninfo.ion
            self.memsions[index].shutter = ioninfo.shutter

    def setupUi(self, parent):
        MemsPositionsForm.setupUi(self, parent)
        self.MemsPositionsTableModel = MemsPositionsTableModel(self.memsions, self.globalDict)
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

        self.okButton.clicked.connect( self.onOk )
        self.cancelButton.clicked.connect( self.onCancel )

        # self.MemsPositionsTableModel.frequencyChanged.connect( self.onFrequency )
        # self.MemsPositionsTableModel.phaseChanged.connect( self.onPhase )
        # self.MemsPositionsTableModel.amplitudeChanged.connect( self.onAmplitude )
        # self.MemsPositionsTableModel.enableChanged.connect( self.onEnableChanged )
        # self.MemsPositionsTableModel.squareChanged.connect( self.onSquareChanged )
        # self.pulser.shutterChanged.connect( self.onShutterChanged )
        restoreGuiState(self, self.config.get(self.guiStateConfigName))

    def persistCallback(self, source, data):
        time, value, minval, maxval = data
        unit = None
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
        self.persistence.persist(self.persistSpace, source, time, value, minval, maxval, unit)

    def saveConfig(self):
        self.config[self.ionConfigName] = self.memsions
        self.config[self.autoApplyConfigName] = self.autoApply
        self.config[self.guiStateConfigName] = saveGuiState(self)
        
    def onOk(self):
        pass
        ## Save all values to globals.
        # ionObj = self.memsions[ion]
        # ion = ionObj.ion
        # self.ad9912.setFrequency(ion, value)
        # if self.autoApply: self.onApply()
        # self.decimation[(0, ion)].decimate(time.time(), value, partial(self.persistCallback, "Frequency:{0}".format(
        #     ionObj.name if ionObj.name else ion)))

    def onCancel(self):
        pass
        # close window (don't save values)

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
