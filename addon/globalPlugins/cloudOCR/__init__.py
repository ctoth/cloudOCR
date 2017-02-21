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

import json

import beep_sequence
import ocrspace
sys.path.remove(PLUGIN_DIR)


class OCRTextInfo(textInfos.offsets.OffsetsTextInfo):

	def __init__(self, point=None, result=None, *args, **kwargs):
		self.point = point
		self.result = result
		super(OCRTextInfo, self).__init__(*args, **kwargs)

	def get_parsed_text(self):
		return self.result[0]['ParsedText']

	def _getStoryText(self):
		return self.get_parsed_text()

	def _getStoryLength(self):
		return len(self._getStoryText())

	def _getTextRange(self, start, end):
		return self.get_parsed_text()[start:end]

	def copy(self):
		return OCRTextInfo(obj=self.obj, position=self.bookmark, point=self.point, result=self.result)

	def _getLineOffsets(self, offset):
		logger.info("offset: ", offset)
		lines = self.get_parsed_text().split('\n')
		start, end = 0, 0
		logger.info("lines: ", len(lines))
		for line in lines:
			line = line + '\n'
			start = end
			end = end + len(line)
			if start <= offset and end > offset:
				return start, end

	def _getPointFromOffset(self, offset):
		start, end = 0, 0
		for word in self.get_words():
			start = end
			end += len(word)
			end += 1
			if offset >= start and offset < end:
				left, top = self.point
				left += word['Left']
				top += word['Top']
				return textInfos.Point(left, top)

	def _getOffsetFromPoint(self, x, y):
		offset = 0
		for word in self.get_words():
			offset += len(word) + 1
			left = word['Left'] + self.point[0]
			top = word['Top'] + self.point[1]
			width = word['Width']
			height = word['Height']
			box = (left, top, left + width, top + height)
			if is_in_box((x, y), box):
				return offset - (len(word) + 1)

	def get_words(self):
		for line in self.result[0]['TextOverlay']['Lines']:
			for word in line['Words']:
				yield word

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
		nav.makeTextInfo = lambda position: OCRTextInfo(obj=nav, position=position, point=(left, top), result=recognised)
		api.setReviewPosition(nav.makeTextInfo(textInfos.POSITION_FIRST))
		beep_sequence.beep_sequence((480, 100))


	__gestures = {
		"kb:shift+NVDA+r": "OCR",
	}

def is_in_box(position, box):
	top, bottom, left, right = box
	x, y = position
	return left <= x < right and bottom <= y < top
