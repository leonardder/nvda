#textUtils.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2018-2019 NV Access Limited, Babbage B.V.

"""
Classes and utilities to deal with strings.
"""

import encodings
import sys
from collections.abc import Sequence, ByteString

defaultStringEncoding = "utf_32_le"

class EncodingAwareString(Sequence):
	"""
	Object that holds a string in both its decoded and its UTF-x encoded form.
	The indexes and length of the resulting objects are based on the byte size of the given encoding.

	First, an instance is created:

	>> string = EncodingAwareString('\U0001f609', encoding="utf_16_le")

	Then, the length of the string can be fetched:

	>>> len(string)
	2

	And the object can be indexed and sliced:

	This example string behaves exactly the same as a Python 2 unicode string, which is stored using a two bytes encoding.
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

	def __mul__(self, value):
		return EncodingAwareString(self.decoded.__mul__(value), self.encoding, self.errors)

	def __rmul__(self, value):
		return EncodingAwareString(self.decoded.__rmul__(value), self.encoding, self.errors)

	def __len__(self):
		return len(self.encoded) // self.bytesPerIndex

	def __getitem__(self, key):
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
			return NotImplemented
		return EncodingAwareString(self.encoded[newKey], self.encoding, self.errors)

	def __contains__(self, char):
		if isinstance(char, ByteString):
			return char in self.encoded
		return char in self.decoded

	def count(self, sub, start=0, end=sys.maxsize):
		if isinstance(sub, str):
			sub = sub.encode(self.encoding, self.errors)
		if not isinstance(sub, ByteString):
			raise TypeError("Expected an object of type str or ByteString")
		start *= self.bytesPerIndex
		end = min(end * self.bytesPerIndex, sys.maxsize)
		return self.encoded.count(sub, start, end) / self.bytesPerIndex

	def find(self, sub, start=0, end=sys.maxsize):
		if isinstance(sub, str):
			sub = sub.encode(self.encoding, self.errors)
		if not isinstance(sub, ByteString):
			raise TypeError("Expected an object of type str or ByteString")
		start *= self.bytesPerIndex
		end = min(end * self.bytesPerIndex, sys.maxsize)
		return self.encoded.find(sub, start, end) / self.bytesPerIndex

	def index(self, sub, start=0, end=sys.maxsize):
		if isinstance(sub, str):
			sub = sub.encode(self.encoding, self.errors)
		if not isinstance(sub, ByteString):
			raise TypeError("Expected an object of type str or ByteString")
		start *= self.bytesPerIndex
		end = min(end * self.bytesPerIndex, sys.maxsize)
		return self.encoded.index(sub, start, end) / self.bytesPerIndex

	def joinByteString(self, seq):
		return EncodingAwareString(self.encoded.join(seq), self.encoding, self.errors)

	def joinStr(self, seq):
		return EncodingAwareString(self.decoded.join(seq), self.encoding, self.errors)

	def rfind(self, sub, start=0, end=sys.maxsize):
		if isinstance(sub, str):
			sub = sub.encode(self.encoding, self.errors)
		if not isinstance(sub, ByteString):
			raise TypeError("Expected an object of type str or ByteString")
		start *= self.bytesPerIndex
		end = min(end * self.bytesPerIndex, sys.maxsize)
		return self.encoded.rfind(sub, start, end) / self.bytesPerIndex

	def rindex(self, sub, start=0, end=sys.maxsize):
		if isinstance(sub, str):
			sub = sub.encode(self.encoding, self.errors)
		if not isinstance(sub, ByteString):
			raise TypeError("Expected an object of type str or ByteString")
		start *= self.bytesPerIndex
		end = min(end * self.bytesPerIndex, sys.maxsize)
		return self.encoded.rindex(sub, start, end) / self.bytesPerIndex
