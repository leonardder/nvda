#minhook.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2019 NV Access Limited, Leonard de Ruijter

""""Wrapper module for the minhook library"""

import ctypes
from contextlib import contextmanager
# MH_STATUS enum
MH_UNKNOWN = -1
MH_OK = 0
MH_ERROR_ALREADY_INITIALIZED = 1
MH_ERROR_NOT_INITIALIZED = 2
MH_ERROR_ALREADY_CREATED = 3
MH_ERROR_NOT_CREATED = 4
MH_ERROR_ENABLED = 5
MH_ERROR_DISABLED = 6
MH_ERROR_NOT_EXECUTABLE = 7
MH_ERROR_UNSUPPORTED_FUNCTION = 8
MH_ERROR_MEMORY_ALLOC = 9
MH_ERROR_MEMORY_PROTECT = 10

MH_ALL_HOOKS = None

def initialize():
	res = ctypes.windll.minhook.MH_Initialize()
	if res:
		raise RuntimeError("minhook MH_Initialize call failed with status code %d" % res)

def uninitialize():
	res = ctypes.windll.minhook.MH_Uninitialize()
	if res:
		raise RuntimeError("minhook MH_Uninitialize call failed with status code %d" % res)

def createHook(functype, target, detour):
	original = 	functype()
	res = ctypes.windll.minhook.MH_CreateHook(target, detour, ctypes.byref(original))
	if res:
		raise RuntimeError("minhook MH_CreateHook call failed with status code %d" % res)
	return original

def enableHook(target):
	res = ctypes.windll.minhook.MH_EnableHook(target)
	if res:
		raise RuntimeError("minhook MH_EnableHook call failed with status code %d" % res)

def disableHook(target):
	res = ctypes.windll.minhook.MH_DisableHook(target)
	if res:
		raise RuntimeError("minhook MH_DisableHook call failed with status code %d" % res)

def removeHook(target):
	res = ctypes.windll.minhook.MH_RemoveHook(target)
	if res:
		raise RuntimeError("minhook MH_RemoveHook call failed with status code %d" % res)

@contextmanager
def temporaryHook(target):
	"""A context manager that temporary enables the specified hook,
	disabling it after leaving the with statement.
	"""
	enableHook(target)
	try:
		yield
	finally:
		disableHook(target)
