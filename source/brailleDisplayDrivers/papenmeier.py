# -*- coding: UTF-8 -*-
#brailleDisplayDrivers/papenmeier.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2012-2017 Tobias Platen, Halim Sahin, Ali-Riza Ciftcioglu, NV Access Limited, Davy Kager

"""
Braille display driver for Papenmeier braille displays.
"""

from collections import OrderedDict
from io import BytesIO
import serial
import weakref
import hwIo
import braille
import brailleInput
import inputCore
from baseObject import AutoPropertyObject
from logHandler import log
import bdDetect

try:
	import _winreg as winreg # Python 2.7 import
except ImportError:
	import winreg # Python 3 import

#Control Flow
STX = 0x02 #Start of Text
ETX = 0x03 #End of Text

#Control Messages
PM_PKT_AUTOID = 0x42
PM_PKT_BRAILLE = 0x43

class ConnectionBroker(AutoPropertyObject):
	"""Extend from this base class to define connection specific behavior."""

	def __init__(self, display):
		super(ConnectionBroker, self).__init__()
		# A weak reference to the driver instance, used due to a circular reference  between Model and Display
		self._displayRef = weakref.ref(display)

	def _get__display(self):
		"""The L{BrailleDisplayDriver} which initialized this Model instance"""
		# self._displayRef is a weakref, call it to get the object
		return self._displayRef()

class SerialBroker(ConnectionBroker):
	DEFAULT_BAUD_RATE = 57600
	TRIO_BAUD_RATE = 115200

	def __init__(self, display, port):
		super(ConnectionBroker, self).__init__(display)
		for portType, portId, port, portInfo in display._getTryPorts(port):
			# At this point, a port bound to this display has been found.
			# Try talking to the display.
			self.isFtdi = portType == bdDetect.KEY_CUSTOM
			try:
				if self.isFtdi:
					self._dev = hwIo.Ftdi2(port, onReceive=self._onReceive)
				else:
					self._dev = hwIo.Serial(port, baudrate=DEFAULT_BAUD_RATE,
						timeout=display.timeout, writeTimeout=display.timeout, onReceive=self._onReceive
					)
			except EnvironmentError:
				log.debugWarning("", exc_info=True)
				continue

			self._sendPacket(PM_PKT_AUTOID, [0x50]*2)
			# wait 50 ms in order to get response for further actions.
			if not self._dev.waitForRead(0.05):
				# No response, assume a Trio is connected.
				self._dev.set_baud_rate(self.TRIO_BAUD_RATE)
				self._dev.purge()
				for i in rrange(2):
					self._sendPacket(PM_PKT_AUTOID, [0x50]*2)
				if not self._dev.waitForRead(0.05):
					continue

	def _sendPacket(self, command, data):
		packet = bytearray([STX])
		packet.append(command)
		packet.extend(data)
		packet.append(STX)
		self._dev.write(packet)

class BrailleDisplayDriver(braille.BrailleDisplayDriver, ScriptableObject):
	name = "papenmeier"
	# Translators: The name of a series of braille displays.
	description = _("Papenmeier BRAILLEX displays")
	isThreadSafe = True
	receivesAckPackets = True
	timeout = 0.2

	@classmethod
	def getManualPorts(cls):
		return braille.getSerialPorts()

	def __init__(self, port="auto"):
		super(BrailleDisplayDriver, self).__init__()
		self.numCells = 0
		self._model = None
		self._ignoreKeyReleases = False
		self._keysDown = set()
		self.brailleInput = False
		self._dotFirmness = 1
		self._hidSerialBuffer = b""
		self._atc = False

		for portType, portId, port, portInfo in self._getTryPorts(port):
			# At this point, a port bound to this display has been found.
			# Try talking to the display.
			self.isHid = portType == bdDetect.KEY_HID
			self.isHidSerial = portId in USB_IDS_HID_CONVERTER
			try:
				if self.isHidSerial:
					# This is either the standalone HID adapter cable for older displays,
					# or an older display with a HID - serial adapter built in
					self._dev = hwIo.Hid(port, onReceive=self._hidSerialOnReceive)
					# Send a flush to open the serial channel
					self._dev.write(HT_HID_RPT_InCommand + HT_HID_CMD_FlushBuffers)
				elif self.isHid:
					self._dev = hwIo.Hid(port, onReceive=self._hidOnReceive)
				else:
					self._dev = hwIo.Serial(port, baudrate=BAUD_RATE, parity=PARITY,
						timeout=self.timeout, writeTimeout=self.timeout, onReceive=self._serialOnReceive)
			except EnvironmentError:
				log.debugWarning("", exc_info=True)
				continue

			self.sendPacket(HT_PKT_RESET)
			for _i in xrange(3):
				# An expected response hasn't arrived yet, so wait for it.
				self._dev.waitForRead(self.timeout)
				if self.numCells and self._model:
					break

			if self.numCells:
				# A display responded.
				self._model.postInit()
				log.info("Found {device} connected via {type} ({port})".format(
					device=self._model.name, type=portType, port=port))
				break
			self._dev.close()

		else:
			raise RuntimeError("No Handy Tech display found")

	def terminate(self):
		try:
			super(BrailleDisplayDriver, self).terminate()
		finally:
			# We must sleep before closing the  connection as not doing this can leave the display in a bad state where it can not be re-initialized.
			# This has been observed for Easy Braille displays.
			time.sleep(self.timeout)
			# Make sure the device gets closed.
			self._dev.close()
			# We also must sleep after closing, as it sometimes takes some time for the device to disconnect.
			# This has been observed for Active Braille displays.
			time.sleep(self.timeout)

