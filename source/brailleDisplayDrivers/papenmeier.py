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
				self._nlk = 0
		self._nrk = 0
		self.decodedKeys = []

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

	def _sendBraillePacket(self, cells, nrk, nlk, nv):
		"""write data to braille cells with nv (vertical cells),
		nrk (cells right) and nlk (cells left).
		some papenmeier displays have vertical cells, other displays have dummy cells with keys.
		"""
		data = bytearray()
		d2 = len(cells) + nv + 2 * nlk + 2 * nrk
		data.append(0x50|(d2 >> 4))
		data.append(0x50|(d2 & 0x0F))
		#fill dummy bytes (left,vertical)
		data.extend([0x30] *2 * nv)
		data.extend([0x30] * 4 * nlk)
		#swap dot bits
		for c in cells:
			swappedC = int('{:08b}'.format(c)[::-1], 2)
			data.append(0x30|(swappedC >> 4))
			data.append(0x30|(swappedC & 0x0F))
		#fill dummy bytes on (right)
		data.extend([0x30] *4 * nrk)
		self._sendPacket(PM_PKT_BRAILLE, data)

	def _onReceive(self, data):
		# The first byte of a packet is STX
		assert ord(data) == STX
		packet = bytearray()
		packetType = self._dev.read(1)			
		packet.append(packetType)
		packet.extend(self._dev.read(2))
		if packetType in ('K', 'L'):
			length = 2*(((packet[1] - 0x50) << 4) + (packet[2] - 0x50))
		else:
			length = 5
		packet.extend(self._dev.read(length))
		lastByte = ord(self._dev.read(1))
		assert lastByte == ETX
		self._handlePacket(packet)

	def _identifyDevice(self, packet):
					if(autoid[3] == 0x35 and autoid[4] == 0x38):#EL80s
						self.numCells = 80
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL80s")
					elif(autoid[3]==0x35 and autoid[4]==0x3A):#EL70s
						self.numCells = 70
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL70s")
					elif(autoid[3]==0x35 and autoid[4]==0x35):#EL40s
						self.numCells = 40
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL40s")
					elif(autoid[3] == 0x35 and autoid[4] == 0x37):#EL66s
						self.numCells = 66
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL66s")
					elif(autoid[3] == 0x35 and autoid[4] == 0x3E):#EL20c
						self.numCells = 20
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL20c")
					elif(autoid[3] == 0x35 and autoid[4] == 0x3F):#EL40c
						self.numCells = 40
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL40c")
					elif(autoid[3] == 0x36 and autoid[4] == 0x30):#EL60c
						self.numCells = 60
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL60c")
					elif(autoid[3] == 0x36 and autoid[4] == 0x31):#EL80c
						self.numCells = 80
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 0
						log.info("Found EL80c")
					elif(autoid[3] == 0x35 and autoid[4] == 0x3b):#EL2D80s
						self.numCells = 80
						self._nlk = 1
						self._nrk = 1
						self._proto = 'A'
						self._voffset = 20
						log.info("Found EL2D80s")
					elif(autoid[3] == 0x35 and autoid[4] == 0x39):#trio
						self.numCells = 40
						self._proto = 'B'
						self._voffset = 0
						log.info("Found trio")
					elif(autoid[3] == 0x36 and autoid[4] == 0x34):#live20
						self.numCells = 20
						self._proto = 'B'
						self._voffset = 0
						log.info("Found live 20")
					elif(autoid[3] == 0x36 and autoid[4] == 0x33):#live+
						self.numCells = 40
						self._proto = 'B'
						self._voffset = 0
						log.info("Found live+")
					elif(autoid[3] == 0x36 and autoid[4] == 0x32):#live
						self.numCells = 40
						self._proto = 'B'
						self._voffset = 0
						log.info("Found live")

	def _handlePacket(self, packet):

	@staticmethod
	def _decode_trio(keys):
		"""decode routing keys on Trio"""
		if(keys[0]=='K' ): #KEYSTATE CHANGED EVENT on Trio, not Braille keys
			keys = keys[3:]
			i = 0
			j = []
			for k in keys:
				a= ord(k)&0x0F
				#convert bitstream to list of indexes
				if(a & 1): j.append(i+3)
				if(a & 2): j.append(i+2)
				if(a & 4): j.append(i+1)
				if(a & 8): j.append(i)
				i +=4
			return j
		return []

	@staticmethod
	def _decodeKeysA(data,start,voffset):
		"""decode routing keys non Trio devices"""
		n = start                           #key index iterator
		j=  []
		shift = 0
		for i in xrange(0,len(data)):	#byte index
			if(i%2==0):
				a= ord(data[i])&0x0F		#n+4,n+3
				b= ord(data[i+1])&0x0F	#n+2,n+1
				#convert bitstream to list of indexes
				if(n > 26): shift=voffset
				if(b & 1): j.append(n+0-shift)
				if(b & 2): j.append(n+1-shift)
				if(b & 4): j.append(n+2-shift)
				if(b & 8): j.append(n+3-shift)
				if(a & 1): j.append(n+4-shift)
				if(a & 2): j.append(n+5-shift)
				if(a & 4): j.append(n+6-shift)
				if(a & 8): j.append(n+7-shift)
				n+=8
		return j

	def _decodeKeyNamesRepeat(self):
		"""translate key names for protocol A with repeat"""
		self._repeatcount+=1
		dec = []
		if(self._repeatcount < 10): return dec
		else: self._repeatcount = 0
		for key in self.decodedKeys:
			try:
				dec.append(self._keynamesrepeat[key])
			except:
				pass
		return dec

	def _decodeKeyNames(self):
		"""translate key names for protocol A"""
		dec = []
		keys = self.decodedKeys
		for key in keys:
			try:
				dec.append(self._keynames[key])
			except:
				pass
		return dec

	def _join_keys(self, dec):
		"""join key names with comma, this is used for key combinations"""
		if(len(dec) == 1): return dec[0]
		elif(len(dec) == 3 and dec[0] == dec[1]): return dec[0] + "," + dec[2]
		elif(len(dec) == 3 and dec[0] == dec[2]): return dec[0] + "," + dec[1]
		elif(len(dec) == 2): return dec[1] + "," + dec[0]
		else: return ''

	def _keyname_decoded(self, key,rest):
		"""convert index used by brxcom to keyname"""
		if(key == 11 or key == 9): return 'l1' + rest
		elif(key == 12 or key == 10): return 'l2' + rest
		elif(key == 13 or key == 15): return 'r1' + rest
		elif(key == 14 or key == 16): return 'r2' + rest

		elif(key == 3): return 'up' + rest
		elif(key == 7): return 'dn' + rest
		elif(key == 1): return 'left' + rest
		elif(key == 5): return 'right' + rest

		elif(key == 4): return 'up2' + rest
		elif(key == 8): return 'dn2' + rest
		elif(key == 2): return 'left2' + rest
		elif(key == 6): return 'right2' + rest
		else: return ''

class BrailleDisplayDriver(braille.BrailleDisplayDriver):
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

