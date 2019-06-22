#XMLFormatting.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2008-2019 NV Access Limited, Babbage B.V.
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

from xml.parsers import expat
import textInfos
from logHandler import log
import textUtils

class XMLTextParser(object): 

	def __init__(self):
		self.parser=expat.ParserCreate('utf-8')
		self.parser.StartElementHandler=self._startElementHandler
		self.parser.EndElementHandler=self._EndElementHandler
		self.parser.CharacterDataHandler=self._CharacterDataHandler
		self._commandList=[]

	def _startElementHandler(self,tagName,attrs):
		if tagName=='unich':
			data=attrs.get('value',None)
			if data is not None:
				try:
					dataInt = int(data)
				except ValueError:
					dataInt = 0xfffd
				# Assumption: we are parsing data from NVDA-helper,
				# which will be wide character data.
				data: bytes = dataInt.to_bytes(2, "little", signed=False)
				self._ByteDataHandler(data)
			return
		elif self._commandList and isinstance(self._commandList[-1], bytes):
			self._commandList[-1] = self._commandList[-1].decode(textUtils.WCHAR_ENCODING, errors="surrogatepass")
		if tagName=='control':
			newAttrs=textInfos.ControlField(attrs)
			self._commandList.append(textInfos.FieldCommand("controlStart",newAttrs))
		elif tagName=='text':
			newAttrs=textInfos.FormatField(attrs)
			self._commandList.append(textInfos.FieldCommand("formatChange",newAttrs))
		else:
			raise ValueError("Unknown tag name: %s"%tagName)

		# Normalise attributes common to both field types.
		try:
			newAttrs["_startOfNode"] = newAttrs["_startOfNode"] == "1"
		except KeyError:
			pass
		try:
			newAttrs["_endOfNode"] = newAttrs["_endOfNode"] == "1"
		except KeyError:
			pass

	def _EndElementHandler(self,tagName):
		if tagName=="control":
			self._commandList.append(textInfos.FieldCommand("controlEnd",None))
		elif tagName in ("text","unich"):
			pass
		else:
			raise ValueError("unknown tag name: %s"%tagName)

	def _ByteDataHandler(self,data: bytes):
		cmdList=self._commandList
		if cmdList and isinstance(cmdList[-1], bytes):
			cmdList[-1]+=data
		else:
			cmdList.append(data)

	def _CharacterDataHandler(self,data):
		cmdList=self._commandList
		if cmdList and isinstance(cmdList[-1],str):
			cmdList[-1]+=data
		else:
			cmdList.append(data)

	def parse(self,XMLText):
		try:
			self.parser.Parse(XMLText)
		except:
			log.error("XML: %s"%XMLText,exc_info=True)
		return self._commandList
