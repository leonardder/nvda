#hwIo/ftdi2.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2019 NV Access Limited, Leonard de Ruijter
#This work is based on a basic ftdi2 wrapper by Jonathan Roadley-Battin.

import ctypes
try:
	ftd2xx = windll.ftd2xx
except WindowsError:
	raise RuntimeError("ftd2xx library not available")
from . import IoBase, _isDebug

FT_OK = 0
FT_LIST_NUMBER_ONLY = 0x80000000
FT_LIST_BY_INDEX = 0x40000000
FT_LIST_ALL = 0x20000000
FT_OPEN_BY_SERIAL_NUMBER = 1
FT_PURGE_RX = 1
FT_PURGE_TX = 2

class FtdiBitModes:
    RESET         = 0x0
    ASYNC_BITBANG = 0x1
    MPSSE         = 0x2
    SYNC_BITBANG  = 0x4
    MCU_HOST      = 0x8
    FAST_SERIAL   = 0x10

class DeviceListInfoNode(c.Structure):
	_fields_ = [
		('Flags',c.c_ulong),
		('Type',c.c_ulong),
		('ID',c.c_ulong),
		('LocID',c.c_ulong),
		('SerialNumber',(c.c_char * 16)),
		('Description',(c.c_char * 64)),
		('none',c.c_void_p),
	]

class Ftdi2(IoBase):
	"""Raw I/O for FTDI serial devices.
	By default, these devices don't offer a serial COM port.
	"""

	def __init__(self, serial, onReceive):
		"""Constructor.
		@param serial: The device serial number.
		@type path: bytes
		@param onReceive: A callable taking a received input report as its only argument.
		@type onReceive: callable(str)
		"""
		if _isDebug():
			log.debug("Opening FTDI device %s" % serial)
		handle = ctypes.c_ulong()
		res = ftd2xx.FT_OpenEx(serial, FT_OPEN_BY_SERIAL_NUMBER, ctypes.byref(handle))
		if res != FT_OK:
			raise RuntimeError("FT_OpenEx failed with error code %d" % res)
		assert handle.value > 0, "Invalid handle"
		super(Ftdi2, self).__init__(handle, onReceive)
		