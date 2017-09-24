# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
from modules.firstNotNone import firstNotNone
from functools import partial
from pulser import MemsPositions

class MemsPositionsTableModel(QtCore.QAbstractTableModel):
    headerDataLookup = ['Ion #', 'x1', 'x1 cal.', 'y1', 'y1 cal.', 'x2', 'x2 cal.', 'y2', 'y2 cal.']

    x1Changed = QtCore.pyqtSignal(object, object)
    x1cChanged = QtCore.pyqtSignal(object, object)
    y1Changed = QtCore.pyqtSignal(object, object)
    y1cChanged = QtCore.pyqtSignal(object, object)
    x2Changed = QtCore.pyqtSignal(object, object)
    x2cChanged = QtCore.pyqtSignal(object, object)
    y2Changed = QtCore.pyqtSignal(object, object)
    y2cChanged = QtCore.pyqtSignal(object, object)

    def __init__(self, memsPositionsChannels, globalDict, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        # scanNames are given as a SortedDict
        self.memsPositionsChannels = memsPositionsChannels
        # self.defaultBG = QtGui.QColor(QtCore.Qt.white)
        # self.textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)

        n = 0
        self.dataLookup = {  (QtCore.Qt.DisplayRole, n): lambda row: str(row+1),
                             (QtCore.Qt.DisplayRole, n+1): lambda row: str(self.memsPositionsChannels[row].x1),
                             (QtCore.Qt.DisplayRole, n+2): lambda row: str(self.memsPositionsChannels[row].x1c),
                             (QtCore.Qt.DisplayRole, n+3): lambda row: str(self.memsPositionsChannels[row].y1),
                             (QtCore.Qt.DisplayRole, n+4): lambda row: str(self.memsPositionsChannels[row].y1c),
                             (QtCore.Qt.DisplayRole, n+5): lambda row: str(self.memsPositionsChannels[row].x2),
                             (QtCore.Qt.DisplayRole, n+6): lambda row: str(self.memsPositionsChannels[row].x2c),
                             (QtCore.Qt.DisplayRole, n+7): lambda row: str(self.memsPositionsChannels[row].y2),
                             (QtCore.Qt.DisplayRole, n+8): lambda row: str(self.memsPositionsChannels[row].y2c),

                             (QtCore.Qt.EditRole, n+1): lambda row: firstNotNone( self.memsPositionsChannels[row].x1Text, str(self.memsPositionsChannels[row].x1)),
                             (QtCore.Qt.EditRole, n+2): lambda row: firstNotNone( self.memsPositionsChannels[row].x1cText, str(self.memsPositionsChannels[row].x1c)),
                             (QtCore.Qt.EditRole, n+3): lambda row: firstNotNone(self.memsPositionsChannels[row].y1Text, str(self.memsPositionsChannels[row].y1)),
                             (QtCore.Qt.EditRole, n+4): lambda row: firstNotNone(self.memsPositionsChannels[row].y1cText, str(self.memsPositionsChannels[row].y1c)),
                             (QtCore.Qt.EditRole, n+5): lambda row: firstNotNone(self.memsPositionsChannels[row].x2Text, str(self.memsPositionsChannels[row].x2)),
                             (QtCore.Qt.EditRole, n+6): lambda row: firstNotNone(self.memsPositionsChannels[row].x2cText, str(self.memsPositionsChannels[row].x2c)),
                             (QtCore.Qt.EditRole, n+7): lambda row: firstNotNone(self.memsPositionsChannels[row].y2Text, str(self.memsPositionsChannels[row].y2)),
                             (QtCore.Qt.EditRole, n+8): lambda row: firstNotNone(self.memsPositionsChannels[row].y2cText, str(self.memsPositionsChannels[row].y2c)),

                             # (QtCore.Qt.BackgroundColorRole, n+1): lambda row: self.defaultBG if self.memsPositionsChannels[row].x1Text is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+2): lambda row: self.defaultBG if self.memsPositionsChannels[row].x1cText is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+3): lambda row: self.defaultBG if self.memsPositionsChannels[row].y1Text is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+4): lambda row: self.defaultBG if self.memsPositionsChannels[row].y1cText is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+5): lambda row: self.defaultBG if self.memsPositionsChannels[row].x2Text is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+6): lambda row: self.defaultBG if self.memsPositionsChannels[row].x2cText is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+7): lambda row: self.defaultBG if self.memsPositionsChannels[row].y2Text is None else self.textBG,
                             # (QtCore.Qt.BackgroundColorRole, n+8): lambda row: self.defaultBG if self.memsPositionsChannels[row].y2cText is None else self.textBG,
                             }

        self.setDataLookup = { (QtCore.Qt.EditRole, n+1): self.setx1,
                               (QtCore.Qt.EditRole, n+2): self.setx1c,
                               (QtCore.Qt.EditRole, n+3): self.sety1,
                               (QtCore.Qt.EditRole, n+4): self.sety1c,
                               (QtCore.Qt.EditRole, n+5): self.setx2,
                               (QtCore.Qt.EditRole, n+6): self.setx2c,
                               (QtCore.Qt.EditRole, n+7): self.sety2,
                               (QtCore.Qt.EditRole, n+8): self.sety2c,
                               (QtCore.Qt.UserRole, n+1): partial( self.setFieldText, 'x1Text'),
                               (QtCore.Qt.UserRole, n+2): partial( self.setFieldText, 'x1cText'),
                               (QtCore.Qt.UserRole, n+3): partial( self.setFieldText, 'y1Text'),
                               (QtCore.Qt.UserRole, n+4): partial( self.setFieldText, 'y1cText'),
                               (QtCore.Qt.UserRole, n+5): partial( self.setFieldText, 'x2Text'),
                               (QtCore.Qt.UserRole, n+6): partial( self.setFieldText, 'x2cText'),
                               (QtCore.Qt.UserRole, n+7): partial( self.setFieldText, 'y2Text'),
                               (QtCore.Qt.UserRole, n+8): partial( self.setFieldText, 'y2cText'),


                               }

        self.globalDict = globalDict

    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)

    def setx1(self, index, value):
        self.memsPositionsChannels[index.row()].x1 = value
        self.x1Changed.emit( index.row(), value)
        return True

    def setx1c(self, index, value):
        self.memsPositionsChannels[index.row()].x1c = value
        self.x1cChanged.emit( index.row(), value)
        return True

    def sety1(self, index, value):
        self.memsPositionsChannels[index.row()].y1 = value
        self.y1Changed.emit(index.row(), value)
        return True

    def sety1c(self, index, value):
        self.memsPositionsChannels[index.row()].y1c = value
        self.y1cChanged.emit(index.row(), value)
        return True

    def setx2(self, index, value):
        self.memsPositionsChannels[index.row()].x2 = value
        self.x2Changed.emit(index.row(), value)
        return True

    def setx2c(self, index, value):
        self.memsPositionsChannels[index.row()].x2c = value
        self.x2cChanged.emit(index.row(), value)
        return True

    def sety2(self, index, value):
        self.memsPositionsChannels[index.row()].y2 = value
        self.y2Changed.emit(index.row(), value)
        return True

    def sety2c(self, index, value):
        self.memsPositionsChannels[index.row()].y2c = value
        self.y2cChanged.emit(index.row(), value)
        return True

    def setFieldText(self, fieldname, index, value):
        setattr( self.memsPositionsChannels[index.row()], fieldname, value )
        return True

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.memsPositionsChannels)
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 9
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
    
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False)(index, value)
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable if index.column() in [0, 9] else QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
            elif (orientation == QtCore.Qt.Vertical):
                return str(section)
        return None  # QtCore.QVariant()
