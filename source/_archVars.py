#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2020 NV Access Limited, Leonard de Ruijter
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

"""NVDA architectural vars."""

import platform

pythonArchitecture= platform.architecture()[0]

supportedPythonArchitectures = (
	"32bit",
	"64bit",
)

helperArchitectures = (
	"X86",
	"x86_64",
	"arm64"
)

pythonToHelperArchitectures = {
	"32bit": "x86",
	"64bit": "x86_64",
}

mainHelperArchitecture = pythonToHelperArchitectures[pythonArchitecture]

otherHelperArchitectures = tuple(arch for arch in helperArchitectures if arch != mainHelperArchitecture)