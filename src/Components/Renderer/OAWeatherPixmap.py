# Copyright (C) 2023 jbleyel
#
# OAWeather is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dogtag is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OAWeather.  If not, see <http://www.gnu.org/licenses/>.

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, BT_SCALE, BT_KEEP_ASPECT_RATIO, BT_HALIGN_CENTER, BT_VALIGN_CENTER


class OAWeatherPixmap(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.iconFileName = ""

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		instance.setPixmapScaleFlags(BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] != self.CHANGED_CLEAR:
				pngname = self.source.iconfilename
			if pngname == "":
				self.instance.hide()
			else:
				self.instance.show()
				if self.iconFileName != pngname:
					self.instance.setPixmapFromFile(pngname)
					self.iconFileName = pngname
