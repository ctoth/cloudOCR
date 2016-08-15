
from collections import namedtuple
from globalPluginHandler import GlobalPlugin
import logging
logger = logging.getLogger(__name__)
import os
import sys
import tempfile
###Path shananagans since we have to ship so many random bits of the stdlib with NVDA Addons
PLUGIN_DIR = os.path.dirname(__file__)
sys.path.append(PLUGIN_DIR)

import addonHandler
addonHandler.initTranslation()
import api
import textInfos



# Add bundled copy of PIL to module search path.
sys.path.append(os.path.join(PLUGIN_DIR, "PIL"))
import ImageGrab
del sys.path[-1]

import beep_sequence
import ocrspace
sys.path.remove(PLUGIN_DIR)

OcrWord = namedtuple("OcrWord", ("offset", "left", "top"))

class OCRParser(object):

	def __init__(self, data, leftCoordOffset, topCoordOffset):
		self._leftCoordOffset = leftCoordOffset
		self._topCoordOffset = topCoordOffset
		self.textLen = 0
		self.lines = []
		self.words = []

class OCRTextInfo(textInfos.offsets.OffsetsTextInfo):

	def __init__(self, result=None, *args, **kwargs):
		self.result = result
		super(OCRTextInfo, self).__init__(*args, **kwargs)

	def _getStoryText(self):
		return self.get_text()

	def _getStoryLength(self):
		return len(self.get_text())

	def get_text(self):
		return self.result[0]['ParsedText']

	def copy(self):
		return OCRTextInfo(obj=self.obj, position=self.bookmark, result=self.result)

class GlobalPlugin(GlobalPlugin):
	scriptCategory = _("Cloud OCR")

	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		self.OCR_API = ocrspace.OCRSpaceAPI(key='3c42208a1588957')


	def script_OCR(self, gesture):
		"""OCR the contents of the current navigator object using a remote, cloud-based service."""
		nav = api.getNavigatorObject()
		left, top, width, height = nav.location
		screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
		temp_path = tempfile.mktemp(suffix='.png')
		screenshot.save(temp_path)
		beep_sequence.beep_sequence((333, 50), 25, (666, 50), 25, (999, 50))
		recognised = None
		with open(temp_path, mode='rb') as screenshot_png:
			try:
				recognised = self.OCR_API.OCR_file(screenshot_png, overlay=True)
			except ocrspace.APIError:
				beep_sequence.beep_sequence((137, 50), 25, (137, 50))
		os.unlink(temp_path)
		if recognised is None:
			return
		nav.makeTextInfo = lambda position: OCRTextInfo(obj=nav, position=position, result=recognised)
		api.setReviewPosition(nav.makeTextInfo(textInfos.POSITION_FIRST))
		beep_sequence.beep_sequence((480, 100))


	__gestures = {
		"kb:shift+NVDA+r": "OCR",
	}

