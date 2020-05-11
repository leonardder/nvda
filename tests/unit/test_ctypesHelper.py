# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2020 NV Access Limited, Leonard de Ruijter

"""Unit tests for the ctypesHelper module.
"""

import unittest
import winUser
import ctypes
import ctypes.wintypes
from ctypesHelper import annotatedCFunction

class TestAnnotatedCFunction(unittest.TestCase):
	"""
	Tests for the annotatedCFunction function decorator.
	Tests are performed with the user32 GetCursorPos function, which gets the position of the mouse pointer.
	The position is copied to ctypes.wintypes.POINT as an out param (lpPoint).
	While ctypes has support for out params (i.e. it can provide an empty structure automatically),
	we can yet use this function to test in param behavior as well.
	"""

	def setUp(self):
		# Set the cursor pos at a point we know.
		winUser.setCursorPos(50, 50)

	def test_setCursorPos_noErrorNoReturnNoOutParam(self):

		@annotatedCFunction(winUser.user32, discardReturnValue=True)
		def GetCursorPos(lpPoint: ctypes.wintypes.LPPOINT) -> ctypes.wintypes.BOOL:
			...

		# Construct an empty Point strucutre