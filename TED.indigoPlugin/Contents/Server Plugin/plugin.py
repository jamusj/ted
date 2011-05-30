# This is an Indigo 5.0 plugin to support The Energy Detective 1000-series
#
# Copyright (C) 2011 by Jamus Jegier
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import ted
import sys
import threading
import functools
import Queue

class Plugin(indigo.PluginBase):
  def __init__(self, 
         pluginId, 
         pluginDisplayName, 
         pluginVersion, 
         pluginPrefs):
     indigo.PluginBase.__init__(self,pluginId,pluginDisplayName,pluginVersion,pluginPrefs)
     self.tedThreads={}
     self.properties={}

  def __del__(self):
     indigo.PluginBase.__def__(self)

  
  # Stop the TED monitoring thread
  def deviceStopComm(self,dev):
    indigo.server.log("Stop")
    if dev.id in self.tedThreads:
        self.stopThread = True
        tedThread = self.tedThreads[dev.id]
        tedThread.join()
        del tedThread


  # Populates a TED device's self.properties
  def loadProperties(self,dev):
    propertyEntry={}
    propertyEntry["poll"]=delay=dev.pluginProps.get(u"poll", u"")
    if dev.pluginProps.get(u"enableCurrentKwVariable", u""):
      propertyEntry["currentKwVariableName"]=dev.pluginProps.get(u"currentKwVariableName", u"")
    if dev.pluginProps.get(u"enableDayKwhVariable", u""):
      propertyEntry["dayKwhVariableName"]=dev.pluginProps.get(u"dayKwhVariableName", u"")
    if dev.pluginProps.get(u"enableMonthKwhVariable", u""):
      propertyEntry["monthKwhVariableName"]=dev.pluginProps.get(u"monthKwhVariableName", u"")
    if dev.pluginProps.get(u"enableVoltsVariable", u""):
      propertyEntry["voltsVariableName"]=dev.pluginProps.get(u"voltsVariableName", u"")
    self.properties[dev.id]=propertyEntry

  def _tedThread(self,tedInstance,dev):
    while True:
      try:
        while True:
          propertyEntry=self.properties[dev.id]
          for packet in tedInstance.poll():
            dev.updateStateOnServer("current_kw",value=packet.fields['kw'])
            dev.updateStateOnServer("kwH_today",value=packet.fields['kwH_today'])
            dev.updateStateOnServer("kwH_month",value=packet.fields['kwH_month'])
            dev.updateStateOnServer("volts",value=packet.fields['volts'])
            if "currentKwVariableName" in propertyEntry:
              indigo.variable.updateValue(propertyEntry["currentKwVariableName"],value=str(packet.fields['kw']))
            if "dayKwhVariableName" in propertyEntry:
              indigo.variable.updateValue(propertyEntry["dayKwhVariableName"],value=str(packet.fields['kwH_today']))
            if "monthKwhVariableName" in propertyEntry:
              indigo.variable.updateValue(propertyEntry["monthKwhVariableName"],value=str(packet.fields['kwH_month']))
            if "voltsVariableName" in propertyEntry:
              indigo.variable.updateValue(propertyEntry["voltsVariableName"],value=str(packet.fields['volts']))
          self.sleep(float(propertyEntry["poll"]))
      except self.StopThread:
        break
      except ProtocolError:
          ## If tedThread throws an exception, it doesn't go to Indigo, so catch
          ## it and report it
        self.exceptionLog() 
      except:
        self.exceptionLog()
        break
    tedInstance.close() 

  # Start TED monitoring thread
  def deviceStartComm(self,dev):
    self.stopThread = False
    indigo.server.log("Start")
    device=dev.pluginProps.get(u"dev", u"")
    self.loadProperties(dev)
   
    tedInstance = ted.TED(device)
    tedThread = threading.Thread(
                                 target=functools.partial(self._tedThread,tedInstance,dev)
                                 )
    tedThread.start()
    self.tedThreads[dev.id]=tedThread

  # Call parent deviceUpdated; reload configuration
  def deviceUpdated(self, origDev, newDev):
    indigo.PluginBase.deviceUpdated(self,origDev,newDev)
    if newDev.pluginId == self.pluginId:
      self.loadProperties(newDev)

  # The serial device we consider a comm property and requires a thread
  # restart, the rest can be changed on the fly
  def didDeviceCommPropertyChange(self, origDev, newDev):
    olddevice=origDev.pluginProps.get(u"dev", u"")
    newdevice=newDev.pluginProps.get(u"dev", u"") 
    return olddevice!=newdevice
  
  # This is to wake up the device thread during a shutdown
  def _preShutdown(self):
    self.stopThread = True
    indigo.PluginBase._preShutdown(self)
