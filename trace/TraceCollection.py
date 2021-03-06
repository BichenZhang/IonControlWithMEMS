# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from collections import defaultdict
from datetime import datetime
from dateutil import parser
import io
from itertools import zip_longest
import math
import os.path
import h5py
import copy

import numpy

from modules.XmlUtilit import prettify
from modules.enum import enum
import xml.etree.ElementTree as ElementTree
import time
from modules.SequenceDictSignal import SequenceDictSignal as SequenceDict
import pytz
from modules.DataDirectory import DataDirectory
import logging
from collections import OrderedDict

try:
    from fit import FitFunctions
    FitFunctionsAvailable = True
except:
    FitFunctionsAvailable = False

filetypes = {'.hdf': 'hdf5', '.hdf5': 'hdf5', '.txt': 'text'}
extensions = {'text': '.txt', 'hdf5': '.hdf5'}

def file_type(filename, default):
    return filetypes.get(os.path.splitext(filename)[1], default)


def replaceExtension(filename, extension):
    extension = extension if extension[0] == '.' else '.{0}'.format(extension)
    return os.path.splitext(filename)[0] + extension


class TraceException(Exception):
    pass

class ColumnSpec(list):
    def toXmlElement(self, root):
        myElement = ElementTree.SubElement(root, 'ColumnSpec', {})
        myElement.text = ", ".join( self )
        return myElement
    
    @staticmethod
    def fromXmlElement(element):
        return ColumnSpec( element.text.split(", ") )
    
class TracePlotting(object):
    Types = enum('default','steps')
    def __init__(self, xColumn='x',yColumn='y',topColumn=None,bottomColumn=None,heightColumn=None,
                 rawColumn=None,name="",type_ =None, xAxisUnit=None, xAxisLabel=None, windowName=None ):       
        self.xColumn = xColumn
        self.yColumn = yColumn
        self.topColumn = topColumn
        self.bottomColumn = bottomColumn
        self.heightColumn = heightColumn
        self.rawColumn = rawColumn
        self.fitFunction = None
        self.name = name
        self.xAxisUnit = xAxisUnit
        self.xAxisLabel = xAxisLabel
        self.type = TracePlotting.Types.default if type_ is None else type_
        self.windowName = windowName
        
    def __setstate__(self, d):
        self.__dict__ = d
        self.__dict__.setdefault( 'xAxisUnit', None )
        self.__dict__.setdefault( 'xAxisLabel', None )
        self.__dict__.setdefault( 'windowName', None)
        
    attrFields = ['xColumn','yColumn','topColumn', 'bottomColumn','heightColumn', 'name', 'type', 'xAxisUnit', 'xAxisLabel', 'windowName']

class TracePlottingList(list):        
    def toXmlElement(self, root):
        myElement = ElementTree.SubElement(root, 'TracePlottingList', {})
        for traceplotting in self:
            traceplottingElement = ElementTree.SubElement(myElement, 'TracePlotting', dict( (name,str(getattr(traceplotting,name))) for name in TracePlotting.attrFields))
            if traceplotting.fitFunction:
                traceplotting.fitFunction.toXmlElement(traceplottingElement)
        return myElement

    def toHdf5(self, group):
        mygroup = group.require_group('TracePlottingList')
        for traceplotting in self:
            g = mygroup.require_group(traceplotting.name)
            for name in TracePlotting.attrFields:
                g.attrs[name] = getattr(traceplotting, name)
            if traceplotting.fitFunction:
                traceplotting.fitFunction.toHdf5(g)

    @staticmethod
    def fromXmlElement(element):
        l = TracePlottingList()
        for plottingelement in element.findall("TracePlotting"):
            plotting = TracePlotting()
            plotting.__dict__.update( plottingelement.attrib )
            plotting.type = int(plotting.type) if hasattr(plotting,'type') else 0
            if plottingelement.find("FitFunction") is not None:
                plotting.fitFunction = FitFunctions.fromXmlElement( plottingelement.find("FitFunction") )
            l.append(plotting)
        return l

    @staticmethod
    def fromHdf5(group):
        l = TracePlottingList()
        for name, g in group.items():
            plotting = TracePlotting()
            plotting.__dict__.update( g.attrs )
            if "FitFunction" in g:
                plotting.fitFunction = FitFunctions.fromHdf5( g.get("FitFunction"))
            l.append(plotting)
        return l
    
    def __str__(self):
        return "TracePlotting length {0}".format(len(self))        

varFactory = { 'str': str,
               'datetime': lambda s: parser.parse(s), #datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f'),
               'float': float,
               'int': int }


class keydefaultdict(OrderedDict):
    def __init__(self, default_factory, *args):
        super().__init__(*args)
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            ret = self[key] = self.default_factory(self, key)
            return ret


class TraceCollection(keydefaultdict):
    """ Class to encapsulate a collection of traces with a common array of x values (or a single trace).

    This class contains the data for all the traces, and takes care of saving and loading the traces from file
    It inherits from defaultdict and the dictionary holds the columns

    Attributes:
        x (list[float]): array of x values
        y (list[float]): array of y values for single trace
        name (str): name associated with trace collection
        description (dict): description data
        description["comment"] (str): comment to add to file
        description["traceCreation"] (str): the time the collection was created
        filenamePattern (str): filename pattern to use when saving the trace
        autosave (bool): if True, trace collection will be saved as soon as filenamePattern is set
        saved (bool): True if trace collection has been saved
        filename (str): full path to file
        fileleaf (str): name only
        filepath (str): path only
        columnNames (list[str]): all column names in the saved file
    """
    def __init__(self, record_timestamps=False):
        super(TraceCollection, self).__init__(self.defaultColumn)
        """Construct a trace object."""
        self.name = "noname" #name to display in table of traces
        self.description = SequenceDict()
        self.description["comment"] = ""
        self.description["name"] = ""
        self.description["traceCreation"] = datetime.now(pytz.utc)
        self.autoSave = False
        self.saved = False
        self._filenamePattern = None
        self._fileType = 'text'
        self.filename = None
        self.filepath = None
        self.fileleaf = None
        self.rawdata = None
        self.description["tracePlottingList"] = TracePlottingList()
        self.record_timestamps = record_timestamps

    def __bool__(self):
        return True  # to remain backwards compatible with previous behavior

    @staticmethod
    def defaultColumn(d, key):
        if key == 'indexColumn' and 'x' in d:
            return numpy.arange(0, len(d['x']), 1)
        return numpy.array([])

    def varFromXmlElement(self, element, description):       
        name = element.attrib['name']
        mytype = element.attrib['type']
        if mytype=='dict':
            mydict = SequenceDict()
            for subelement in element:
                self.varFromXmlElement(subelement, mydict)
            description[name] = mydict
        else:
            value = varFactory.get( mytype, str)( element.text )
            description[name] = value
            if name=='comment' and mytype=='str' and not element.text:
                description[name] = '' #avoid comments being set to the string 'None'
            if name=='name' and mytype=='str' and not element.text:
                description[name] = '' #avoid comments being set to the string 'None'

    def recordTimeinterval(self, timeTickOffset):
        self.description['timeTickOffset'] = timeTickOffset
        self['timeTickFirst']
        self['timeTickLast']
    
    def timeintervalAppend(self, timeinterval, maxPoints=0):
        if 0 < maxPoints < len(self["timeTickFirst"]):
            self['timeTickFirst'] = numpy.append(self['timeTickFirst'][-maxPoints+1:0], timeinterval[0])
            self['timeTickLast'] = numpy.append(self['timeTickLast'][-maxPoints+1:0], timeinterval[1])
        else:
            self['timeTickFirst'] = numpy.append(self['timeTickFirst'], timeinterval[0])
            self['timeTickLast'] = numpy.append(self['timeTickLast'], timeinterval[1])
        self.description["lastDataAquired"] = datetime.now(pytz.utc)
    
    @property
    def timeinterval(self):
        return (self['timeTickFirst'], self[ 'timeTickLast'] )
    
    @timeinterval.setter
    def timeinterval(self, val):
        self['timeTickFirst'], self['timeTickLast'] = val

    @property
    def x(self):
        return self['x']

    @x.setter
    def x(self, val):
        self['x'] = val

    @property
    def y(self):
        return self['y']
        
    @y.setter
    def y(self,val):
        self['y'] = val

    @property
    def comment(self):
        return self.description['comment']
    
    @comment.setter
    def comment(self, comment):
        self.description['comment'] = comment

    @property
    def tracename(self):
        return self.description['name']

    @tracename.setter
    def tracename(self, name):
        self.description['name'] = name

    @property
    def xUnit(self):
        return self.description.get('xUnit')
    
    @xUnit.setter
    def xUnit(self, magnitude):
        self.description['xUnit'] = magnitude
        
    @property
    def yUnit(self):
        return self.description.get('yUnit')
    
    @yUnit.setter
    def yUnit(self, magnitude):
        self.description['yUnit'] = magnitude

    @property
    def traceCreation(self):
        return self.description['traceCreation']

    @traceCreation.setter
    def traceCreation(self, date):
        self.description['traceCreation'] = date

    @property
    def filenamePattern(self):
        """Get the pattern of the file name"""
        return self._filenamePattern if self._filenamePattern else 'Untitled'

    @filenamePattern.setter
    def filenamePattern(self, pattern):
        """Set the filenamePattern. Use 'Untitled' as default. Save if autoSave is on."""
        self._filenamePattern = pattern if pattern else 'Untitled'
        self._fileType = file_type(pattern, self._fileType)
        if self.autoSave: self.save()

    def save(self, fileType=None, saveCopy=False):
        """save the trace to file"""
        if saveCopy or not self.saved:
            if fileType and fileType != self._fileType:
                self.filenamePattern = replaceExtension(self.filenamePattern, extensions[fileType])
                self._fileType = fileType
            self.filename, (self.filepath, name, ext) = DataDirectory().sequencefile(self.filenamePattern)
            self.fileleaf = name+ext
        elif fileType and fileType != self._fileType:
            self.filename = replaceExtension(self.filename, extensions[fileType])
            self._fileType = fileType
        if self._fileType == "text":
            self.saveText(self.filename)
        else:
            self.saveHdf5(self.filename)
        return self.filename

    def saveText(self, filename):
        if self.rawdata:
            self.description["rawdata"] = self.rawdata.save()
        if hasattr(self,'fitfunction'):
            self.description["fitfunction"] = self.fitfunction
        if filename:
            of = open(filename,'w')
            columnspec = ColumnSpec(self.keys())
            self.description["columnspec"] = columnspec #",".join(columnspec)
            self.saveTraceHeaderXml(of)
            for l in zip_longest(*list(self.values()), fillvalue=float('NaN')):
                print("\t".join(map(repr,l)), file=of)
            of.close()
            self.saved = True

    def saveHdf5(self, filename):
        # if self.rawdata:
        #     self.description["rawdata"] = self.rawdata.save()
        if hasattr(self,'fitfunction'):
            self.description["fitfunction"] = self.fitfunction
        if filename:
            with h5py.File(filename) as of:
                self.saveMetadata(of)
                colgroup = of.require_group('columns')
                for name, data in self.items():
                    colgroup.pop(name, None)
                    colgroup.create_dataset(name, data=data)
        self.saved = True

    def plot(self,penindex):
        """ plot the data, penindex >= 0 gives requests the style with this number,
        penindex = -1 uses the first available style, penindex = -2 uses the previous style
        """
        if hasattr( self, 'plotfunction' ):
            (self.plotfunction)(self,penindex)
    
    def varstr(self,name):
        """return the variable value as a string"""
        return str(self.description.get(name,""))
        
    def saveTraceHeader(self,outfile):
        """ save the header of the trace to outfile
        """
        self.description["fileCreation"] = datetime.now(pytz.utc)
        self.description.sort()
        for var, value in self.description.items():
            print("# {0}\t{1}".format(var, value), file=outfile)

    def saveTraceHeaderXml(self,outfile):
        root = ElementTree.Element('DataFileHeader')
        varsElement = ElementTree.SubElement(root, 'Variables', {})
        self.description.sort()
        for name, value in self.description.items():
            self.saveDescriptionElement(name, value, varsElement)
        outfile.write(prettify(root,'# '))

    def saveMetadata(self, f):
        variables = f.require_group('variables')
        for name, value in self.description.items():
            self.saveMetadataElement(name, value, variables)

    def saveMetadataElement(self, name, value, variables):
        if hasattr(value,'toHdf5'):
            value.toHdf5(variables)
        if isinstance(value, dict):
            dictgroup = variables.require_group(name)
            for name_, value_ in value.items():
                self.saveMetadataElement(name_, value_, dictgroup)
        elif isinstance(value, (int, float)):
            variables.attrs[name] = value
        else:
            variables.attrs[name] = str(value)

    def saveDescriptionElement(self, name, value, element):
        if hasattr(value,'toXmlElement'):
            value.toXmlElement(element)
        elif isinstance(value, dict):
            subElement = ElementTree.SubElement(element, 'Element', {'name': name, 'type': 'dict'})
            for subname, subvalue in value.items():
                self.saveDescriptionElement(subname, subvalue, subElement)           
        else:
            e = ElementTree.SubElement(element, 'Element', {'name': name, 'type': type(value).__name__})
            e.text = str(value)

    def loadTrace(self, filename):
        self._fileType = file_type(filename, self._fileType)
        if self._fileType == "hdf5":
            self.loadTraceHdf5(filename)
        else:
            self.loadTracePlain(filename)

    def loadTraceHdf5(self, filename):
        with h5py.File(self.filename) as f:
            for colname, dataset in f['columns'].items():
                self[colname] = numpy.array(dataset)
            tpelement = f.get("/variables/TracePlottingList")
            self.description["tracePlottingList"] = TracePlottingList.fromHdf5(tpelement) if tpelement is not None else None
            # for element in root.findall("/variables/Element"):
            #     self.varFromXmlElement(element, self.description)

    def loadTracePlain(self, filename):
        with io.open(filename,'r') as instream:
            position = instream.tell()
            firstline = instream.readline()
            instream.seek(position)
            if firstline.find("<?xml version")>0:
                self.loadTraceXml(instream)
            else:
                self.loadTraceText(instream)
                self.description["tracePlottingList"].append(TracePlotting())
        self.filename = filename

    def loadTraceXml(self, stream):
        xmlstringlist = []
        data = []
        for line in stream:
            if line[0]=="#":
                xmlstringlist.append(line.lstrip("# "))
            else:
                data.append( list(map(float,line.split())) )
        root = ElementTree.fromstringlist(xmlstringlist)
        columnspec = ColumnSpec.fromXmlElement(root.find("./Variables/ColumnSpec"))
        for colname, d in zip(columnspec, zip(*data)):
            if math.isnan(d[-1]):
                a = numpy.array(d[0:-1])
            else:
                a = numpy.array(d)
            self[colname] = a
        tpelement = root.find("./Variables/TracePlottingList")
        self.description["tracePlottingList"] = TracePlottingList.fromXmlElement(tpelement) if tpelement is not None else None
        for element in root.findall("./Variables/Element"):
            self.varFromXmlElement(element, self.description)

    def loadTraceText(self, stream):
        data = []
        self.description["columnspec"] = "x,y"
        for line in stream:
            line = line.strip()
            if not line or line[0]=='#':
                line = line.lstrip('# \t\r\n')
                if line.find('\t')<0:
                    a = line.split(None,1)
                else:
                    a = line.split('\t',1)
                if len(a)>1:
                    self.description[a[0]] = a[1]  
            else:
                data.append( list(map(float,line.split())) )
        columnspec =  self.description["columnspec"].split(',')
        for colname, d in zip( columnspec, zip(*data) ):
            self[colname] = numpy.array(d)
        if 'fitfunction' in self.description and FitFunctionsAvailable:
            self.fitfunction = FitFunctions.fitFunctionFactory(self.description["fitfunction"])
        self.description["tracePlottingList"] = [TracePlotting(xColumn='x',yColumn='y',topColumn=None,bottomColumn=None,heightColumn=None, rawColumn=None,name="")]
            
    def setPlotfunction(self, callback):
        self.plotfunction = callback
        
    def addTracePlotting(self, traceplotting):
        self.description["tracePlottingList"].append(traceplotting)
        
    @property 
    def tracePlottingList(self):
        return self.description["tracePlottingList"]

if __name__=="__main__":
    import sys
    import gc
    t = TraceCollection()
    print(sys.getrefcount(t))
    del t
    gc.collect()
