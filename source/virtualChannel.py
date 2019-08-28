import os
import sys
sys.path.append(os.path.dirname(__file__))
import sourceEnv
import winsound
winsound.Beep(440, 300)
import comtypes.gen
import comtypesMonkeyPatches
import comInterfaces
comtypes.gen.__path__.append(comInterfaces.__path__[0])
from comInterfaces import NVDAVirtualChannel
import comtypes
import comtypes.server.localserver
from ctypes import POINTER, pointer

class NVDAVirtualChannelPlugin(NVDAVirtualChannel.NVDA):
	_reg_threading_ = "Free"
	_reg_desc_ = "NVDA Virtual Channel Plugin Class"
	_reg_progid_ = "NVDAVirtualChannel.NVDA.1"
	_reg_novers_progid_ = "NVDAVirtualChannel.NVDA"
	_reg_clsctx_ = comtypes.CLSCTX_LOCAL_SERVER
	_regcls_ = comtypes.server.localserver.REGCLS_MULTIPLEUSE

	def Initialize(self, pChannelMgr):
		listenerCallback = self.QueryInterface(NVDAVirtualChannel.IWTSListenerCallback)
		self._listener = pChannelMgr.CreateListener("echo", 0, listenerCallback)

	def Connected(self):
		return

	def Disconnected(dwDisconnectCode):
		return

	def Terminated(self):
		return

if __name__ == "__main__":
	from comtypes.server.register import UseCommandLine
	UseCommandLine(NVDAVirtualChannelPlugin)
