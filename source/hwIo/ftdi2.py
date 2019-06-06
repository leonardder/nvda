#hwIo/ftdi2.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2019 NV Access Limited, Leonard de Ruijter
#This work is based on a basic ftdi2 wrapper by Jonathan Roadley-Battin.

from . import Serial as HwIoSerial
import ctypes
from serial import win32, SerialException, Serial

class Ftdi2Serial(Serial):

	def _reconfigurePort(self):
		try:
			super(Ftdi2Serial, self)._reconfigurePort()
		except ValueError:
			pass

	def inWaiting(self):
		raise NotImplementedError

	def read(self, size=1):
		if size > 0:
			win32.ResetEvent(self._overlappedRead.hEvent)
			buf = ctypes.create_string_buffer(size)
			rc = win32.DWORD()
			err = win32.ReadFile(self.hComPort, buf, size, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
			if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
				raise SerialException("ReadFile failed (%r)" % ctypes.WinError())
			err = win32.WaitForSingleObject(self._overlappedRead.hEvent, win32.INFINITE)
			read = buf.raw[:rc.value]
		else:
			read = bytes()
		return bytes(read)

class Ftdi2(HwIoSerial):
	_SerialClass = Ftdi2Serial