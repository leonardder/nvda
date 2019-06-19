# -*- coding: UTF-8 -*-
#tests/unit/test_textUtils.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2019 NV Access Limited, Babbage B.V., Leonard de Ruijter

"""Unit tests for the textUtils module."""

import unittest
from textUtils import WideStringOffsetConverter

class TestStrToWideOffsets(unittest.TestCase):
	"""
	Tests that ensure that offsets in a string are properly converted to wide string offsets.
	Every string offset for 32-bit unicode characters (e.g. emoji) take two offsets in a wide string representation.
	"""

	def test_nonSurrogate(self):
		converter = WideStringOffsetConverter(text="abc")
		self.assertEqual(converter.wideStringLength, 3)
		self.assertEqual(converter.strToWideOffsets(0, 0), (0, 0))
		self.assertEqual(converter.strToWideOffsets(0, 1), (0, 1))
		self.assertEqual(converter.strToWideOffsets(0, 2), (0, 2))
		self.assertEqual(converter.strToWideOffsets(0, 3), (0, 3))
		self.assertEqual(converter.strToWideOffsets(1, 1), (1, 1))
		self.assertEqual(converter.strToWideOffsets(1, 2), (1, 2))
		self.assertEqual(converter.strToWideOffsets(1, 3), (1, 3))
		self.assertEqual(converter.strToWideOffsets(2, 2), (2, 2))
		self.assertEqual(converter.strToWideOffsets(2, 3), (2, 3))
		self.assertEqual(converter.strToWideOffsets(3, 3), (3, 3))

	def test_surrogatePairs(self):
		converter = WideStringOffsetConverter(text=u"\U0001f926\U0001f60a\U0001f44d") # 🤦😊👍
		self.assertEqual(converter.wideStringLength, 6)
		self.assertEqual(converter.strToWideOffsets(0, 0), (0, 0))
		self.assertEqual(converter.strToWideOffsets(0, 1), (0, 2))
		self.assertEqual(converter.strToWideOffsets(0, 2), (0, 4))
		self.assertEqual(converter.strToWideOffsets(0, 3), (0, 6))
		self.assertEqual(converter.strToWideOffsets(1, 1), (2, 2))
		self.assertEqual(converter.strToWideOffsets(1, 2), (2, 4))
		self.assertEqual(converter.strToWideOffsets(1, 3), (2, 6))
		self.assertEqual(converter.strToWideOffsets(2, 2), (4, 4))
		self.assertEqual(converter.strToWideOffsets(2, 3), (4, 6))
		self.assertEqual(converter.strToWideOffsets(3, 3), (6, 6))

	def test_mixedSurrogatePairsAndNonSurrogates(self):
		converter = WideStringOffsetConverter(text=u"a\U0001f926b") # a🤦b
		self.assertEqual(converter.wideStringLength, 4)
		self.assertEqual(converter.strToWideOffsets(0, 0), (0, 0))
		self.assertEqual(converter.strToWideOffsets(0, 1), (0, 1))
		self.assertEqual(converter.strToWideOffsets(0, 2), (0, 3))
		self.assertEqual(converter.strToWideOffsets(0, 3), (0, 4))
		self.assertEqual(converter.strToWideOffsets(1, 1), (1, 1))
		self.assertEqual(converter.strToWideOffsets(1, 2), (1, 3))
		self.assertEqual(converter.strToWideOffsets(1, 3), (1, 4))
		self.assertEqual(converter.strToWideOffsets(2, 2), (3, 3))
		self.assertEqual(converter.strToWideOffsets(2, 3), (3, 4))
		self.assertEqual(converter.strToWideOffsets(3, 3), (4, 4))

	def test_mixedSurrogatePairsNonSurrogatesAndSingleSurrogates(self):
		"""
		Tests surrogate pairs, non surrogates as well as
		single surrogate characters (i.e. incomplete pairs)
		"""
		converter = WideStringOffsetConverter(text=u"a\ud83e\U0001f926\udd26b")
		self.assertEqual(converter.wideStringLength, 6)
		self.assertEqual(converter.strToWideOffsets(0, 0), (0, 0))
		self.assertEqual(converter.strToWideOffsets(0, 1), (0, 1))
		self.assertEqual(converter.strToWideOffsets(0, 2), (0, 2))
		self.assertEqual(converter.strToWideOffsets(0, 3), (0, 4))
		self.assertEqual(converter.strToWideOffsets(0, 4), (0, 5))
		self.assertEqual(converter.strToWideOffsets(0, 5), (0, 6))
		self.assertEqual(converter.strToWideOffsets(1, 1), (1, 1))
		self.assertEqual(converter.strToWideOffsets(1, 2), (1, 2))
		self.assertEqual(converter.strToWideOffsets(1, 3), (1, 4))
		self.assertEqual(converter.strToWideOffsets(1, 4), (1, 5))
		self.assertEqual(converter.strToWideOffsets(1, 5), (1, 6))
		self.assertEqual(converter.strToWideOffsets(2, 2), (2, 2))
		self.assertEqual(converter.strToWideOffsets(2, 3), (2, 4))
		self.assertEqual(converter.strToWideOffsets(2, 4), (2, 5))
		self.assertEqual(converter.strToWideOffsets(2, 5), (2, 6))
		self.assertEqual(converter.strToWideOffsets(3, 3), (4, 4))
		self.assertEqual(converter.strToWideOffsets(3, 4), (4, 5))
		self.assertEqual(converter.strToWideOffsets(3, 5), (4, 6))
		self.assertEqual(converter.strToWideOffsets(4, 4), (5, 5))
		self.assertEqual(converter.strToWideOffsets(4, 5), (5, 6))
		self.assertEqual(converter.strToWideOffsets(5, 5), (6, 6))

class TestWideToStrOffsets(unittest.TestCase):
	"""
	Tests that ensure that offsets in a wide string are properly converted to str offsets.
	Every string offset for 32-bit unicode characters (e.g. emoji) take two offsets in a wide string representation.
	"""

	def test_nonSurrogate(self):
		converter = WideStringOffsetConverter(text="abc")
		self.assertEqual(converter.strLength, 3)
		self.assertEqual(converter.wideToStrOffsets(0, 0), (0, 0))
		self.assertEqual(converter.wideToStrOffsets(0, 1), (0, 1))
		self.assertEqual(converter.wideToStrOffsets(0, 2), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(0, 3), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(1, 1), (1, 1))
		self.assertEqual(converter.wideToStrOffsets(1, 2), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(1, 3), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(2, 2), (2, 2))
		self.assertEqual(converter.wideToStrOffsets(2, 3), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(3, 3), (3, 3))

	def test_surrogatePairs(self):
		converter = WideStringOffsetConverter(text=u"\U0001f926\U0001f60a\U0001f44d") # 🤦😊👍
		self.assertEqual(converter.strLength, 3)
		self.assertEqual(converter.wideToStrOffsets(0, 0), (0, 0))
		self.assertEqual(converter.wideToStrOffsets(0, 1), (0, 1))
		self.assertEqual(converter.wideToStrOffsets(0, 2), (0, 1))
		self.assertEqual(converter.wideToStrOffsets(0, 3), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(0, 4), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(0, 5), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(0, 6), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(1, 1), (0, 0))
		self.assertEqual(converter.wideToStrOffsets(1, 2), (0, 1))
		self.assertEqual(converter.wideToStrOffsets(1, 3), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(1, 4), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(1, 5), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(1, 6), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(2, 2), (1, 1))
		self.assertEqual(converter.wideToStrOffsets(2, 3), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(2, 4), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(2, 5), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(2, 6), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(3, 3), (1, 1))
		self.assertEqual(converter.wideToStrOffsets(3, 4), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(3, 5), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(3, 6), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(4, 4), (2, 2))
		self.assertEqual(converter.wideToStrOffsets(4, 5), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(4, 6), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(5, 5), (2, 2))
		self.assertEqual(converter.wideToStrOffsets(5, 6), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(6, 6), (3, 3))

	def test_mixedSurrogatePairsAndNonSurrogates(self):
		converter = WideStringOffsetConverter(text=u"a\U0001f926b") # a🤦b
		self.assertEqual(converter.strLength, 3)
		self.assertEqual(converter.wideToStrOffsets(0, 0), (0, 0))
		self.assertEqual(converter.wideToStrOffsets(0, 1), (0, 1))
		self.assertEqual(converter.wideToStrOffsets(0, 2), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(0, 3), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(0, 4), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(1, 1), (1, 1))
		self.assertEqual(converter.wideToStrOffsets(1, 2), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(1, 3), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(1, 4), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(2, 2), (1, 1))
		self.assertEqual(converter.wideToStrOffsets(2, 3), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(2, 4), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(3, 3), (2, 2))
		self.assertEqual(converter.wideToStrOffsets(3, 4), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(4, 4), (3, 3))

	def test_mixedSurrogatePairsNonSurrogatesAndSingleSurrogates(self):
		"""
		Tests surrogate pairs, non surrogates as well as
		single surrogate characters (i.e. incomplete pairs)
		"""
		converter = WideStringOffsetConverter(text=u"a\ud83e\U0001f926\udd26b")
		self.assertEqual(converter.strLength, 5)
		self.assertEqual(converter.wideToStrOffsets(0, 0), (0, 0))
		self.assertEqual(converter.wideToStrOffsets(0, 1), (0, 1))
		self.assertEqual(converter.wideToStrOffsets(0, 2), (0, 2))
		self.assertEqual(converter.wideToStrOffsets(0, 3), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(0, 4), (0, 3))
		self.assertEqual(converter.wideToStrOffsets(0, 5), (0, 4))
		self.assertEqual(converter.wideToStrOffsets(0, 6), (0, 5))
		self.assertEqual(converter.wideToStrOffsets(1, 1), (1, 1))
		self.assertEqual(converter.wideToStrOffsets(1, 2), (1, 2))
		self.assertEqual(converter.wideToStrOffsets(1, 3), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(1, 4), (1, 3))
		self.assertEqual(converter.wideToStrOffsets(1, 5), (1, 4))
		self.assertEqual(converter.wideToStrOffsets(1, 6), (1, 5))
		self.assertEqual(converter.wideToStrOffsets(2, 2), (2, 2))
		self.assertEqual(converter.wideToStrOffsets(2, 3), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(2, 4), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(2, 5), (2, 4))
		self.assertEqual(converter.wideToStrOffsets(2, 6), (2, 5))
		self.assertEqual(converter.wideToStrOffsets(3, 3), (2, 2))
		self.assertEqual(converter.wideToStrOffsets(3, 4), (2, 3))
		self.assertEqual(converter.wideToStrOffsets(3, 5), (2, 4))
		self.assertEqual(converter.wideToStrOffsets(3, 6), (2, 5))
		self.assertEqual(converter.wideToStrOffsets(4, 4), (3, 3))
		self.assertEqual(converter.wideToStrOffsets(4, 5), (3, 4))
		self.assertEqual(converter.wideToStrOffsets(4, 6), (3, 5))
		self.assertEqual(converter.wideToStrOffsets(5, 5), (4, 4))
		self.assertEqual(converter.wideToStrOffsets(5, 6), (4, 5))
		self.assertEqual(converter.wideToStrOffsets(6, 6), (5, 5))

