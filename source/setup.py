# -*- coding: UTF-8 -*-
#setup.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2006-2018 NV Access Limited, Peter Vágner, Joseph Lee
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import os
import copy
import gettext
gettext.install("nvda")
from distutils.core import setup
import py2exe as py2exeModule
from glob import glob
import fnmatch
from versionInfo import *
from py2exe import distutils_buildexe
from py2exe.dllfinder import DllFinder
import wx
import sourceEnv
import imp

RT_MANIFEST = 24
manifest_template = r"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
	<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
		<security>
			<requestedPrivileges>
				<requestedExecutionLevel
					level={level}
					uiAccess="{uiAccess}">
				</requestedExecutionLevel>
			</requestedPrivileges>
		</security>
	</trustInfo>
</assembly>
"""

def getModuleExtention(thisModType):
	for ext,mode,modType in imp.get_suffixes():
		if modType==thisModType:
			return ext
	raise ValueError("unknown mod type %s"%thisModType)

# py2exe's idea of whether a dll is a system dll appears to be wrong sometimes, so monkey patch it.
orig_determine_dll_type = DllFinder.determine_dll_type
def determine_dll_type(self, imagename):
	dll = os.path.basename(imagename).lower()
	if dll.startswith("api-ms-win-") or dll in ("powrprof.dll", "mpr.dll", "crypt32.dll"):
		# These are definitely system dlls available on all systems and must be excluded.
		# Including them can cause serious problems when a binary build is run on a different version of Windows.
		return None
	return orig_determine_dll_type(self, imagename)
DllFinder.determine_dll_type = determine_dll_type

class py2exe(distutils_buildexe.py2exe):
	"""Overridden py2exe command to:
		* Add a command line option --enable-uiAccess to enable uiAccess for the main executable
	"""

	user_options = distutils_buildexe.py2exe.user_options + [
		("enable-uiAccess", "u", "enable uiAccess for the main executable"),
	]

	def initialize_options(self):
		super(py2exe, self).initialize_options()
		self.enable_uiAccess = False

	def run(self):
		dist = self.distribution
		if self.enable_uiAccess:
			# Add a target for nvda_uiAccess, using nvda_noUIAccess as a base.
			target = copy.deepcopy(dist.windows[0])
			target["dest_base"] = "nvda_uiAccess"
			target["uac_info"] = (target["uac_info"][0], True)
			dist.windows.insert(1, target)
			# nvda_eoaProxy should have uiAccess.
			target = dist.windows[3]
			target["uac_info"] = (target["uac_info"][0], True)

		super(py2exe, self).run()

	def build_manifest(self, target, template):
		mfest, rid = super(py2exe, self).build_manifest(target, template)
		if getattr(target, "script", "").endswith(".pyw"):
			# This is one of the main application executables.
			mfest = mfest[:mfest.rindex("</assembly>")]
			mfest += MAIN_MANIFEST_EXTRA + "</assembly>"
		return mfest, rid

def getLocaleDataFiles():
	wxDir=wx.__path__[0]
	localeMoFiles=set()
	for f in glob("locale/*/LC_MESSAGES"):
		localeMoFiles.add((f, (os.path.join(f,"nvda.mo"),)))
		wxMoFile=os.path.join(wxDir,f,"wxstd.mo")
		if os.path.isfile(wxMoFile):
			localeMoFiles.add((f,(wxMoFile,))) 
		lang=os.path.split(os.path.split(f)[0])[1]
		if '_' in lang:
				lang=lang.split('_')[0]
				f=os.path.join('locale',lang,'lc_messages')
				wxMoFile=os.path.join(wxDir,f,"wxstd.mo")
				if os.path.isfile(wxMoFile):
					localeMoFiles.add((f,(wxMoFile,))) 
	localeDicFiles=[(os.path.dirname(f), (f,)) for f in glob("locale/*/*.dic")]
	NVDALocaleGestureMaps=[(os.path.dirname(f), (f,)) for f in glob("locale/*/gestures.ini")]
	return list(localeMoFiles)+localeDicFiles+NVDALocaleGestureMaps

def getRecursiveDataFiles(dest,source,excludes=()):
	rulesList=[]
	rulesList.append((dest,
		[f for f in glob("%s/*"%source) if not any(fnmatch.fnmatch(f,exclude) for exclude in excludes) and os.path.isfile(f)]))
	[rulesList.extend(getRecursiveDataFiles(os.path.join(dest,dirName),os.path.join(source,dirName),excludes=excludes)) for dirName in os.listdir(source) if os.path.isdir(os.path.join(source,dirName)) and not dirName.startswith('.')]
	return rulesList

compiledModExtention = getModuleExtention(imp.PY_COMPILED)
sourceModExtention = getModuleExtention(imp.PY_SOURCE)
setup(
	name = name,
	version=version,
	description=description,
	url=url,
	classifiers=[
'Development Status :: 3 - Alpha',
'Environment :: Win32 (MS Windows)',
'Topic :: Adaptive Technologies'
'Intended Audience :: Developers',
'Intended Audience :: End Users/Desktop',
'License :: OSI Approved :: GNU General Public License (GPL)',
'Natural Language :: English',
'Programming Language :: Python',
'Operating System :: Microsoft :: Windows',
],
	cmdclass={"py2exe": py2exe},
	windows=[
		{
			"script":"nvda.pyw",
			"dest_base":"nvda_noUIAccess",
			"uac_info": ("asInvoker", False),
			"icon_resources":[(1,"images/nvda.ico")],
			"version":formatBuildVersionString(),
			"description":"NVDA application",
			"product_version":version,
			"copyright":copyright,
			"company_name":publisher,
		},
		# The nvda_uiAccess target will be added at runtime if required.
		{
			"script": "nvda_slave.pyw",
			"icon_resources": [(1,"images/nvda.ico")],
			"version":formatBuildVersionString(),
			"description": name,
			"product_version": version,
			"copyright": copyright,
			"company_name": publisher,
		},
		{
			"script": "nvda_eoaProxy.pyw",
			# uiAccess will be enabled at runtime if appropriate.
			"uac_info": ("asInvoker", False),
			"icon_resources": [(1,"images/nvda.ico")],
			"version":formatBuildVersionString(),
			"description": "NVDA Ease of Access proxy",
			"product_version": version,
			"copyright": copyright,
			"company_name": publisher,
		},
	],
	options = {"py2exe": {
		"bundle_files": 3,
		"excludes": ["Tkinter",
			"serial.loopback_connection", "serial.rfc2217", "serial.serialcli", "serial.serialjava", "serial.serialposix", "serial.socket_connection"],
		"packages": ["NVDAObjects","virtualBuffers","appModules","comInterfaces","brailleDisplayDrivers","synthDrivers"],
		"includes": [
			"nvdaBuiltin",
			# The previous service executable used win32api, which some add-ons use for various purposes.
			"win32api",
		],
	}},
	data_files=[
		(".",glob("*.dll")+glob("*.manifest")+["builtin.dic"]),
		("documentation", ['../copying.txt', '../contributors.txt']),
		("lib/%s"%version, glob("lib/*.dll")),
		("lib64/%s"%version, glob("lib64/*.dll") + glob("lib64/*.exe")),
		("libArm64/%s"%version, glob("libArm64/*.dll") + glob("libArm64/*.exe")),
		("waves", glob("waves/*.wav")),
		("images", glob("images/*.ico")),
		("louis/tables",glob("louis/tables/*")),
		("COMRegistrationFixes", glob("COMRegistrationFixes/*.reg")),
		(".", ['message.html' ])
	] + (
		getLocaleDataFiles()
		+ getRecursiveDataFiles("synthDrivers", "synthDrivers",
			excludes=(
				"*%s" % sourceModExtention,
				"*%s" % compiledModExtention,
				"*.exp",
				"*.lib",
				"*.pdb",
				"__pycache__"
		))
		+ getRecursiveDataFiles("brailleDisplayDrivers", "brailleDisplayDrivers",
			excludes=(
				"*%s"%sourceModExtention,
				"*%s"%compiledModExtention,
				"__pycache__"
		))
		+ getRecursiveDataFiles('documentation', '../user_docs', excludes=('*.t2t', '*.t2tconf', '*/developerGuide.*'))
	),
)
