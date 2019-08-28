import sourceEnv
import comtypes.gen
import comtypesMonkeyPatches
import comInterfaces
comtypes.gen.__path__.append(comInterfaces.__path__[0])
from comInterfaces import NVDAVirtualChannel
import comtypes
import comtypes.server.localserver

class NVDAVirtualChannelPlugin(NVDAVirtualChannel.NVDA):
	_com_interfaces_ = [
		NVDAVirtualChannel.IWTSPlugin,
	]
	_reg_threading_ = "Free"
	_reg_progid_ = "NVDAVirtualChannel.NVDA.1"
	_reg_novers_progid_ = "NVDAVirtualChannel.NVDA"
	_reg_clsctx_ = comtypes.CLSCTX_INPROC_SERVER | comtypes.CLSCTX_LOCAL_SERVER
	_regcls_ = comtypes.server.localserver.REGCLS_MULTIPLEUSE
if __name__ == "__main__":
	from comtypes.server.register import UseCommandLine
	UseCommandLine(NVDAVirtualChannelPlugin)
