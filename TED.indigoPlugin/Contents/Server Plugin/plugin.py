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

  def __del__(self):
     indigo.PluginBase.__def__(self)

  def deviceStopComm(self,dev):
    if dev.id in self.tedThreads:
        tedThread = self.tedThreads[dev.id]
        tedThread.join()
        del tedThread

  def _tedThread(self,tedInstance,dev):
    try:
      delay=dev.pluginProps.get(u"poll", u"")
      while True:
        for packet in tedInstance.poll():
          dev.updateStateOnServer("current_kw",value=packet.fields['kw'])
          dev.updateStateOnServer("kwH_today",value=packet.fields['kwH_today'])
          dev.updateStateOnServer("kwH_month",value=packet.fields['kwH_month'])
          dev.updateStateOnServer("volts",value=packet.fields['volts'])
          self.sleep(float(delay))
    except self.StopThread:
      pass
    except:
        ## If tedThread throws an exception, it doesn't go to Indigo, so catch
        ## it and report it
      self.exceptionLog() 
    finally:
      tedInstance.close() 

  def deviceStartComm(self,dev):
    device=dev.pluginProps.get(u"dev", u"")
   
    tedInstance = ted.TED(device)
    tedThread = threading.Thread(
                                 target=functools.partial(self._tedThread,tedInstance,dev)
                                 )
    tedThread.start()
    self.tedThreads[dev.id]=tedThread

  def _preShutdown(self):
    self.stopThread = True
    indigo.PluginBase._preShutdown(self)
