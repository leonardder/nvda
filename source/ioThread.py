# -*- coding: UTF-8 -*-
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2006-2019 NV Access Limited, Leonard de Ruijter

from typing import Iterable, Union, Tuple, List, Optional
import ctypes.wintypes
import threading
import winKernel
import extensionPoints
import winUser
from abc import abstractmethod, ABCMeta

class IOThread(threading.Thread, metaclass=ABCMeta):
	"""A background thread used for background writes and raw input/output.
	This is primarily used for braille display I/O,
	but can also be used for other I/O situations.
	"""

	exit = False
	queuedWrite = None

	def __init__(self):
		super().__init__()
		self.queuedWriteLock = threading.Lock()
		self.daemon = True
		self.handle = ctypes.windll.kernel32.OpenThread(winKernel.THREAD_SET_CONTEXT, False, self.ident)

	def queueApc(self, func, param=0):
		ctypes.windll.kernel32.QueueUserAPC(func, self.handle, param)

	def stop(self, timeout=None) -> bool:
		if not self.is_alive():
			raise RuntimeError("Thread already stopped, safe to destroy instance")
		self.exit = True
		# Wake up the thread. It will exit when it sees exit is True.
		self.queueApc(self.executor)
		self.join(timeout)
		if self.is_alive():
			return False
		self.exit = False
		winKernel.closeHandle(self.handle)
		self.handle = None
		return True

	@abstractmethod
	@winKernel.PAPCFUNC
	def executor(self, param):
		if self.exit:
			# func will see this and exit.
			return
		with self.queuedWriteLock:
			data = self.queuedWrite
			self.queuedWrite = None
		if not data:
			return

	def run(self):
		while True:
			ctypes.windll.kernel32.SleepEx(winKernel.INFINITE, True)
			if self.exit:
				break
