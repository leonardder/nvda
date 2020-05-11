# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2020 NV Access Limited, Leonard de Ruijter
# This file may be used under the terms of the GNU General Public License, version 2 or later.
# For more details see: https://www.gnu.org/licenses/gpl-2.0.html

"""Helper functions for external library interop with ctypes."""

import ctypes
from typing import Any, Callable, Union, Optional, Tuple,get_type_hints
from inspect import signature, _empty, Parameter
from dataclasses import dataclass
from logHandler import log
from functools import wraps


class AnnotationError(ValueError):
	...


@dataclass
class OutParam:
	"""Type to specify C style functions output parameters."""
	default: Any = _empty


def parameterToParamFlagsTuple(param):
	isOutParam = isinstance(param.default, OutParam)
	direction = 2 if isOutParam else 1
	name = param.name
	default = param.default.default if isOutParam else param.default
	if default is _empty:
		return (direction, name)
	return (direction, name, default)


def errCheckFactory(
		paramFlags: Tuple[Tuple],
		*,
		errCheckCallable: Optional[Callable[[Any], bool]],
		errRaiseCallable: Callable[[], Exception],
		discardReturnValue: bool
):
	def _errCheck(result, func, args):
		if not discardReturnValue and result is None and issubclass(func.restype, ctypes.c_void_p):
			# ctypes returns None for a null pointer, yet we return 0 because:
			# * discardReturnValue is False
			# * NVDA expects 0 instead of None for most NULL handles
			result = 0
		if errCheckCallable is not None and errCheckCallable(result):
			raise errRaiseCallable()
		if discardReturnValue:
			result = None
			# when returning args, ctypes will return the output arguments if any, or the result, which we set to None.
			return args
		# Filter the arguments for the out params, if any, since we might want to return them
		outArgs = tuple(
			arg for arg, direction
			in zip(args, (f[0] for f in paramFlags))
			if direction == 2
		)
		if not outArgs:
			return result
		return (result, ) + outArgs
	return _errCheck


def annotatedCFunction(
		library: ctypes.CDLL,
		nameOrOrdinal: Optional[Union[str, int]] = None,
		typeFactory: Callable = ctypes.WINFUNCTYPE,
		*,
		errCheckCallable: Optional[Callable[[Any], bool]] = lambda res: res in (None, 0),
		errRaiseCallable: Callable[[], Exception] = ctypes.WinError,
		discardReturnValue: bool = False
):
	def wrap(func):
		if not get_type_hints(func):
			raise AnnotationError(f"{func.__qualname__} stub has no annotations")
		sig = signature(func)
		if sig.return_annotation is _empty:
			raise AnnotationError(f"{func.__qualname__} stub has no return annotation")
		emptyAnnotations = [name for name, param in sig.parameters.items() if param.annotation is _empty]
		if emptyAnnotations:
			emptyAnnotationsStr = ", ".join(emptyAnnotations)
			raise AnnotationError(f"{func.__qualname__} stub has no annotations for parameters {emptyAnnotationsStr}")
		if any(
			param for param in sig.parameters.values()
			if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
		):
			raise ValueError(
				f"{func.__qualname__} contains variable arguments (*args or **kwargs), which is unsupported"
			)
		resType = sig.return_annotation
		argTypes = tuple(param.annotation for param in sig.parameters.values())
		funcType = typeFactory(resType, *argTypes)
		funcSpec = (nameOrOrdinal or func.__name__, library)
		paramFlags = tuple(parameterToParamFlagsTuple(param) for param in sig.parameters.values())
		funcObj = funcType(funcSpec, paramFlags)
		funcObj.errcheck = errCheckFactory(
			paramFlags,
			errCheckCallable=errCheckCallable,
			errRaiseCallable=errRaiseCallable,
			discardReturnValue=discardReturnValue
		)

		@wraps(func)
		def wrapper(*args, **kwargs):
			return funcObj(*args, **kwargs)

		wrapper.funcSpec = funcSpec
		wrapper.paramFlags = paramFlags
		return wrapper
	return wrap
