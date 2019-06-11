#textUtils.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2018-2019 NV Access Limited, Babbage B.V.

"""
Classes and utilities to deal with variable width and multi byte encodings.
"""

import encodings
import sys
try:
	from collections.abc import ByteString # Python 3 import
except ImportError:
	from six import binary_type as ByteString
	from six import text_type as str

class EncodingAwareString(object):
	"""
	Object that holds a string in both its decoded and its UTF-x encoded form.
	The indexes and length of the resulting objects are based on the byte size of the given encoding.

	An instance is created like this:

	>> string = EncodingAwareString('\U0001f609', encoding="utf_16_le")
	"""

	__slots__=("bytesPerIndex", "decoded", "encoded", "encoding", "errors")
	_encodingToBytes = {
		"utf_8": 1,
		"utf_16_le": 2,
		"utf_32_le": 4,
	}

	def __new__(cls, value, encoding, errors="replace"):
		encoding = encodings.normalize_encoding(encoding)
		if encoding not in cls._encodingToBytes:
			raise ValueError("Encoding %s not supported. Supported values are %s" % (
				encoding,
				", ".join(cls._encodingToBytes)
			))
		obj = super(EncodingAwareString, cls).__new__(cls)
		if isinstance(value, ByteString):
			obj.decoded = str(value, encoding, errors)
			obj.encoded = value
		elif isinstance(value, str):
			obj.decoded = value
			obj.encoded = value.encode(encoding, errors)
		else:
			raise TypeError("Value must be of type str or ByteString")
		obj.encoding = encoding
		obj.bytesPerIndex = cls._encodingToBytes[obj.encoding]
		obj.errors = errors
		return obj

	def __repr__(self):
		return "{}({}, encoding={})".format(self.__class__.__name__, repr(self.decoded), self.encoding)

	@property
	def encodingAwareLength(self):
		return len(self.encoded) // self.bytesPerIndex

	def getEncodingAwareOffsets(self, bytesStart, bytesEnd):
		if bytesStart >= len(self.encoded) or bytesEnd >= len(self.encoded):
			raise IndexError("str indexes out of range")
		if self.bytesPerIndex == 1:
			return (bytesStart, bytesEnd)
		return (bytesStart // self.bytesPerIndex, bytesEnd // self.bytesPerIndex)

	def getBytesOffsets(self, encodingAwareStart, encodingAwareEnd):
		if encodingAwareStart >= self.encodingAwareLength or encodingAwareEnd >= self.encodingAwareLength:
			raise IndexError("EncodingAwareString indexes out of range")
		if self.bytesPerIndex == 1:
			return (encodingAwareStart, encodingAwareEnd)
		return (encodingAwareStart * self.bytesPerIndex, encodingAwareEnd * self.bytesPerIndex)

	def encodingAwareGetitem(self, key):
		if isinstance(key, int):
			if key >= len(self):
				raise IndexError("%s index out of range" % EncodingAwareString.__name__)
			start = key * self.bytesPerIndex
			stop = start + self.bytesPerIndex
			newKey = slice(start, stop)
		elif isinstance(key, slice):
			if key.step and key.step > 1:
				# Use our internal joinByteString function here
				start = key.start or 0
				if key.stop is None:
					stop = len(self)
				else:
					stop = min(key.stop, len(self))
				step = key.step
				keys = range(start, stop, step)
				sequence = (self[i].encoded for i in keys)
				return EncodingAwareString("", self.encoding, self.errors).joinByteString(sequence)
			start = key.start
			if start is not None:
				start *= self.bytesPerIndex
			stop = key.stop
			if stop is not None:
				stop *= self.bytesPerIndex
			step = key.step
			newKey = slice(start, stop, step)
		else:
			raise TypeError("Expected int or slice")
		return EncodingAwareString(self.encoded[newKey], self.encoding, self.errors)

	def joinByteString(self, seq):
		return EncodingAwareString(self.encoded.join(seq), self.encoding, self.errors)

	def joinStr(self, seq):
		return EncodingAwareString(self.decoded.join(seq), self.encoding, self.errors)
