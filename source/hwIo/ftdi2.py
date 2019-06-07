#hwIo/ftdi2.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2019 NV Access Limited, Leonard de Ruijter
#This work is based on a basic ftdi2 wrapper by Jonathan Roadley-Battin.

import ctypes
try:
	ftd2xx = ctypes.windll.ftd2xx
except WindowsError:
	raise RuntimeError("ftd2xx library not available")
from . import IoBase, _isDebug
from serial.win32 import (
	FILE_FLAG_OVERLAPPED,
	FILE_ATTRIBUTE_NORMAL,
	ResetEvent,
	COMSTAT,
	COMMTIMEOUTS,
	MAXDWORD,
	INVALID_HANDLE_VALUE
)
import threading
import winKernel
import minhook
from logHandler import log

FT_OK = 0
FT_LIST_NUMBER_ONLY = 0x80000000
FT_LIST_BY_INDEX = 0x40000000
FT_LIST_ALL = 0x20000000
FT_OPEN_BY_SERIAL_NUMBER = 1
FT_PURGE_RX = 1
FT_PURGE_TX = 2

class FtdiBitModes:
	RESET		 = 0x0
	ASYNC_BITBANG = 0x1
	MPSSE		 = 0x2
	SYNC_BITBANG  = 0x4
	MCU_HOST	  = 0x8
	FAST_SERIAL   = 0x10

class DeviceListInfoNode(ctypes.Structure):
	_fields_ = [
		('Flags',ctypes.c_ulong),
		('Type',ctypes.c_ulong),
		('ID',ctypes.c_ulong),
		('LocID',ctypes.c_ulong),
		('SerialNumber',(ctypes.c_char * 16)),
		('Description',(ctypes.c_char * 64)),
		('none',ctypes.c_void_p),
	]

CreateFileA_funcType = ctypes.WINFUNCTYPE(
	ctypes.wintypes.LPCSTR,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.DWORD,
	ctypes.POINTER(winKernel.SECURITY_ATTRIBUTES),
	ctypes.wintypes.DWORD,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.HANDLE
)

class Ftdi2(IoBase):
	"""Raw I/O for FTDI serial devices.
	By default, these devices don't offer a serial COM port.
	"""

	@CreateFileA_funcType
	def _fake_CreateFileA(self, fileName, desiredAccess, shareMode, surityAttributes, creationDisposition, flagsAndAttributes, templateFile):
		res = self._orig_fake_CreateFileA_funcType(fileName, desiredAccess, shareMode, surityAttributes, creationDisposition, flagsAndAttributes, templateFile)
		self._rawHandle = res
		return res

	def __init__(self, serial, onReceive):
		"""Constructor.
		@param serial: The device serial number.
		@type path: bytes
		@param onReceive: A callable taking a received input report as its only argument.
		@type onReceive: callable(str)
		"""
		# When opening a FTDI device using the ftd2xx library,
		# we get a ftd2xx specific handle.
		# We want to use a win32 compatible hanle for asyncronous reading.
		# Therefore, hook CreateFileA in kernel32, which is called by FT_W32_CreateFile.
		self._rawHandle = INVALID_HANDLE_VALUE
		with minhook.temporaryHook(
			winKernel.kernel32.CreateFileA,
			self._fake_CreateFileA,
			CreateFileA_funcType
		) as original:
			# On python 3, this can probably look nicer with a partial object.
			self._orig_fake_CreateFileA = original
			if _isDebug():
				log.debug("Opening FTDI device %s" % serial)
			self._ftHandle = ftd2xx.FT_W32_CreateFile(
				serial,
				winKernel.GENERIC_READ | winKernel.GENERIC_WRITE,
				0,
				None,
				winKernel.OPEN_EXISTING,
				FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED | FT_OPEN_BY_SERIAL_NUMBER,
				None
			)
		self._orig_fake_CreateFileA = None
		if INVALID_HANDLE_VALUE in (self._ftHandle, self._rawHandle):
			lastError = ftd2xx.FT_W32_GetLastError(self._ftHandle)
			if _isDebug():
				log.debug("Open failed: %s" % ctypes.WinError(lastError))
			raise ctypes.WinError(lastError)
		self._syncReadOl = OVERLAPPED()
		super(Ftdi2, self).__init__(self._rawHandle, onReceive, )

	def read(self, size=1):
		# Adapted from serial.win32.Win32Serial
		if size > 0:
			win32.ResetEvent(self._syncReadOl.hEvent)
			buf = ctypes.create_string_buffer()
			receivedBytes = ctypes.wintypes.DWORD()
			if not ftd2xx.FT_W32_ReadFile(self._ftHandle, self._readBuf, self._readSize, ctypes.byref(receivedBytes), ctypes.byref(self._syncReadOl)):
				lastError = ftd2xx.FT_W32_GetLastError(self._ftHandle)
				if lastError != winKernel.ERROR_IO_PENDING:
					ctypes.WinError(lastError)
				if not winKernel.WaitForSingleObject(self._syncReadOl.hEvent, winKernel.INFINITE):
					raise ctypes.WinError()
			read = buf.raw[:receivedBytes.value]
		else:
			read = b""
		return read

	def write(self, data):
		if _isDebug():
			log.debug("Write: %r" % data)
		size = self._writeSize or len(data)
		buf = ctypes.create_string_buffer(size)
		buf.raw = data
		if not ftd2xx.FT_W32_WriteFile(self>-ftHandl, data, size, None, ctypes.byref(self._writeOl)):
			lastError = ftd2xx.FT_W32_GetLastError(self._ftHandle)
			if lastError != ERROR_IO_PENDING:
				if _isDebug():
					log.debug("Write failed: %s" % ctypes.WinError())
				raise ctypes.WinError(lastError)
			bytes = DWORD()
			ftd2xx.FT_W32_GetOverlappedResult(self._writeFile, ctypes.byref(self._writeOl), ctypes.byref(bytes), True)
