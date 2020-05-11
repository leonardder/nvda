# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2020 NV Access Limited, Leonard de Ruijter
# This file may be used under the terms of the GNU General Public License, version 2 or later.
# For more details see: https://www.gnu.org/licenses/gpl-2.0.html

"""Helper functions for external library interop with ctypes."""

import ctypes
from typing import Any, Callable, Union, Optional, Tuple,get_type_hints
from inspect import signature, Signature, _empty, Parameter
from dataclasses import dataclass
from logHandler import log
from functools import wraps


class AnnotationError(ValueError):
	"""Raised by L{annotatedCFunction} when one or more type hints are missing or incorrect.
	"""
	...


@dataclass
class OutParam:
	"""
	Type to specify C style functions output parameters.
	Instances can be used as default values when decorating functions with L{annotatedCFunction}.
	See documentation of L{annotatedCFunction} for examples.
	"""
	#: The real default value for the output parameter.
	default: Any = _empty


def signatureToFuncType(
		sig: Signature,
		funcTypeFactory: Callable
) -> ctypes._CFuncPtr:
	"""Creates a C function type from a L{Signature}.
	@param sig: The signature.
	@param funcTypeFactory: One of ctypes.CFUNCTYPE, ctypes.WINFUNCTYPE or ctypes.PYFUNCTYPE.
	"""
	if sig.return_annotation is _empty:
		raise AnnotationError(f"Signature {sig} has no return annotation")
	emptyAnnotations = [
		name for name, param in sig.parameters.items()
		if param.annotation is _empty
	]
	if emptyAnnotations:
		emptyAnnotationsStr = ", ".join(emptyAnnotations)
		raise AnnotationError(f"Signature {sig} has no annotations for parameters {emptyAnnotationsStr}")
	if any(
		param for param in sig.parameters.values()
		if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
	):
		raise ValueError(
			f"Signature {sig} contains variable arguments (*args or **kwargs), which is unsupported"
		)
	resType = sig.return_annotation
	argTypes = tuple(param.annotation for param in sig.parameters.values())
	return funcTypeFactory(resType, *argTypes)


def _parameterToParamFlag(param: Parameter) -> Tuple:
	"""Converts a L{Parameter} to a ctypes paramflag.
	Any parameter with a defaultvalue of type L{OutParam} will be treated as an output parameter.
	Any other parameters will be treated as input parameter.
	See https://docs.python.org/3/library/ctypes.html#function-prototypes for documentation about paramFlags.
	"""
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
	"""
	Factory to create an error checking function used by L{annotatedCFunction}.
	See https://docs.python.org/3/library/ctypes.html#ctypes._FuncPtr.errcheck for information about
	what ctypes expects from such a function.
	See L{annotatedCFunction} for more information about this factory's parameters.
	"""

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
		funcTypeFactory: Callable = ctypes.WINFUNCTYPE,
		*,
		errCheckCallable: Optional[Callable[[Any], bool]] = None,
		errRaiseCallable: Callable[[], Exception] = ctypes.WinError,
		discardReturnValue: bool = False
):
	"""Annotated C function decorator.

	This decorator can be used to convert a default python style function to a function that wraps a
	C function from an external DLL.
	The decorated function requires type annotations for all its parameters.
	A FUNCTYPE class will be created from the signature of the function using L{signatureToFuncType},
	The behavior of the decorator can be finetuned using the following arguments:
	@param library: The dll that contains the function,
		e.g. ctypes.windll.user32.
	@param nameOrOrdinal: The name or ordinal of the exported function,
		e.g. GetClassNameW.
		If this value is C{None}, the name of the decorated function will be used.
	@param funcTypeFactory: One of ctypes.CFUNCTYPE, ctypes.WINFUNCTYPE or ctypes.PYFUNCTYPE.
	@param errCheckCallable: A callable that receives the result of the function as its only argument,
		returning C{True} if the result indicates an error, C{False} otherwise.
		For example, if a result of 0 means an error,
		the callback could look like: lambda res: res == 0
		If C{None}, no error check will be performed.
	@param errRaiseCallable: A callback returning an exception object that will be raised.
		defaults to ctypes.WinError, which raises the appropriate windows error.
		if L{errCheckCallable} is C{None}, this parameter has no effect.
	@param discardReturnValue: discards the return value of the C function.
		* If C{False} and the function has one or more output parameters, their values are returned.
		* If C{False} and the function has no output parameters, the return value will be C{None}
		* If C{True} and the function has one or more output parameters,
		the return value will be a tuple of the function's result and the output parameter values.
		* If C{False} and the function has no output parameters,
		the return value will be the result of the function.
	"""

	def wrap(func):
		sig = signature(func)
		funcType = signatureToFuncType(sig, funcTypeFactory)
		funcSpec = (nameOrOrdinal or func.__name__, library)
		paramFlags = tuple(_parameterToParamFlag(param) for param in sig.parameters.values())
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
		wrapper._cFunc = funcObj
		return wrapper
	return wrap
