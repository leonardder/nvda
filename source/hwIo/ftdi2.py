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
from serial.win32 import FILE_FLAG_OVERLAPPED, FILE_ATTRIBUTE_NORMAL, ResetEvent, COMSTAT, COMMTIMEOUTS, MAXDWORD
import threading
import winKernel

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

class Ftdi2(Iobase):
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
		handle = ftd2xx.FT_W32_CreateFile(
			serial,
			winKernel.GENERIC_READ | winKernel.GENERIC_WRITE,
			0,
			None,
			winKernel.OPEN_EXISTING,
			FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED | FT_OPEN_BY_SERIAL_NUMBER,
			None
		)
		if handle == INVALID_HANDLE_VALUE:
			lastError = ftd2xx.FT_W32_GetLastError()
			if _isDebug():
				log.debug("Open failed: %s" % ctypes.WinError(lastError))
			raise ctypes.WinError(lastError)
		self._syncReadOl = OVERLAPPED()
		self._readThread = None
		super(Ftdi2, self).__init__(handle, onReceive, )

	def _readThreadFunc(self):
		receivedBytes = ctypes.wintypes.DWORD()
		while true:
			res = ftd2xx.FT_W32_GetOverlappedResult(self.handle, ctypes.byref(self._readOl), ctypes.byref(receivedBytes), True)
			self._	ioDone(ctypes.get_last_error(), receivedBytes, self._readOl)
			if not self._ioDone:
				return

	def _asyncRead(self):
		# ftd2xx has no equivalent of ReadFileEx.
		# Therefore, run a separate threat to wait for the overlapped structure's event.
		if not self._readThread:
			self._readThread = threading.Thread(target=self._readThreadFunc)
			self._readThread.daemon = True
			self._readThread.start()
		# Wait for _readSize bytes of data.
		# _ioDone will call onReceive once it is received.
		# onReceive can then optionally read additional bytes if it knows these are coming.
		bytesRead = ctypes.wintypes.DWORD()
		if ftd2xx.FT_W32_ReadFile(self._file, self._readBuf, self._readSize, ctypes.byref(bytesRead), ctypes.byref(self._readOl)):
			self._	ioDone(ftd2xx.FT_W32_GetLastError(), receivedBytes, self._readOl)

	def read(self, size=1):
		# Adapted from serial.win32.Win32Serial
		if size > 0:
			win32.ResetEvent(self._syncReadOl.hEvent)
			buf = ctypes.create_string_buffer()
			receivedBytes = ctypes.DWORD()
			if not ftd2xx.FT_W32_ReadFile(self._file, self._readBuf, self._readSize, ctypes.byref(receivedBytes), ctypes.byref(self._syncReadOl))
				lastError = ftd2xx.FT_W32_GetLastError()
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
		if not ftd2xx.FT_W32_WriteFile(self._writeFile, data, size, None, ctypes.byref(self._writeOl)):
			lastError = ftd2xx.FT_W32_GetLastError()
			if lastError != ERROR_IO_PENDING:
				if _isDebug():
					log.debug("Write failed: %s" % ctypes.WinError())
				raise ctypes.WinError(lastError)
			bytes = DWORD()
			ftd2xx.FT_W32_GetOverlappedResult(self._writeFile, ctypes.byref(self._writeOl), ctypes.byref(bytes), True)

	def close(self):
		if _isDebug():
			log.debug("Closing")
		self._onReceive = None
		if hasattr(self, "_file") and self._file is not INVALID_HANDLE_VALUE:
			ftd2xx.FT_W32_CancelIo(self._file)
		if hasattr(self, "_writeFile") and self._writeFile not in (self._file, INVALID_HANDLE_VALUE):
			ftd2xx.FT_W32_CancelIo(self._writeFile)
		winKernel.closeHandle(self._recvEvt)
