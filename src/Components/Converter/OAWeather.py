# Copyright (C) 2023 jbleyel, Mr.Servo
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

# Some parts are taken from msnweathercomponent plugin for compatibility reasons.


from Components.Converter.Converter import Converter
from Components.config import config
from Components.Element import cached
from os.path import join, exists
from traceback import print_exc


class OAWeather(Converter, object):
	CURRENT = 0
	DAY1 = 1
	DAY2 = 2
	DAY3 = 3
	DAY4 = 4
	DAY5 = 5
	CITY = 6                    # Example: "Hamburg, Germany"
	TEMPERATURE_HIGH = 7        # Example: "9 °C"
	TEMPERATURE_LOW = 8         # Example: "6 °C"
	TEMPERATURE_TEXT = 9        # Example: "rain showers", HINT: OpenMeteo doesn't deliver descriptiontexts, therefore "N/A" comes up
	TEMPERATURE_CURRENT = 10    # Example: "8 °C"
	WEEKDAY = 11                # Example: "Friday"
	WEEKSHORTDAY = 12           # Example: "Fr"
	DATE = 13                   # Example: "2023-01-13"
	OBSERVATIONTIME = 14        # Example: "16:17"
	OBSERVATIONPOINT = 15       # is no longer supported by the weather services, is now identical with 'CITY'.
	FEELSLIKE = 16              # Example: "4 °C"
	HUMIDITY = 17               # Example: "81 %"
	WINDDISPLAY = 18            # Example: "12 km/h Southwest"
	ICON = 19                   # Example: "9" (matching the extended weather icon code: YAHOO+)
	TEMPERATURE_HIGH_LOW = 20   # Example: "6 - 9 °C"
#   new entries since January 2023
	WEATHERSOURCE = 21          # Example: "MSN Weather"
	LONGITUDE = 22              # Example: "53.5573"
	LATITUDE = 23               # Example: "9.996"
	SUNRISE = 24                # Example: "08:30"
	SUNSET = 25                 # Example: "16:27"
	ISNIGHT = 26                # Example: "False" or "True"
	TEMPUNIT = 27               # Example: "°C"
	WINDUNIT = 28               # Example: "km/h"
	WINDSPEED = 29              # Example: "12 km/h"
	WINDDIR = 30                # Example: "230 °"
	WINDDIRSIGN = 31            # Example: "↗ SW"
	WINDDIRARROW = 31           # Example: "↗"
	WINDDIRNAME = 32            # Example: "Southwest"
	WINDDIRSHORT = 33           # Example: "SW"
	YAHOOCODE = 34              # Example: "9" (matching the extended weather icon code: YAHOO+)
	METEOCODE = 35              # Example: "Q" (matching the character set: MetrixIcons.ttf)

	DAYS = {
		"current": CURRENT,
		"day1": DAY1,
		"day2": DAY2,
		"day3": DAY3,
		"day4": DAY4,
		"day5": DAY5
	}

	def __init__(self, type: str):
		self.enabledebug = config.plugins.OAWeather.debug.value
		Converter.__init__(self, type)
		self.debug("__init__ type:%s" % type)
		self.index = None
		self.mode = None
		self.path = None
		self.extension = "png"
		value = type.split(",")
		self.mode = value[0]
		if len(value) > 1:
			self.index = self.getIndex(value[1].strip())
			if len(value) > 2 and self.mode in ("weathericon", "yahoocode"):
				self.path = value[2].strip()
				if len(value) > 3:
					self.extension = value[3].strip()
		self.debug("__init__ DONE self.mode:%s self.index:%s self.path:%s" % (self.mode, self.index, self.path))
		if config.plugins.OAWeather.debug.value:
			self.getText = self.getTextDebug

	def getIndex(self, key: str):
		self.debug("getIndex key:%s" % (key))
		return self.DAYS.get(key, None)

	@cached
	def getTextDebug(self):
		self.debug("getText mode:%s index:%s" % (self.mode, self.index))
		text = self.getText()
		self.debug("getText mode:%s index:%s value:%s" % (self.mode, self.index, text))
		return text

	@cached
	def getText(self):
		if self.mode:
			try:
				if self.index is not None:
					if self.mode == "temperature_high":
						return self.source.getMaxTemp(self.index)
					elif self.mode == "temperature_low":
						return self.source.getMinTemp(self.index)
					elif self.mode == "temperature_high_low":
						return self.source.getMaxMinTemp(self.index)
					elif self.mode == "temperature_text":
						return self.source.getKeyforDay("text", self.index, "")
					elif self.mode in ("weathericon", "yahoocode"):
						return self.source.getYahooCode(self.index)
					elif self.mode == "meteocode":
						return self.source.getMeteoCode(self.index)
					elif self.mode == "weekday":
						return self.source.getKeyforDay("day", self.index)
					elif self.mode == "weekshortday":
						return self.source.getKeyforDay("shortDay", self.index)
					elif self.mode == "date":
						return self.source.getDate(self.index)
					elif self.mode == "precipitation":
						return self.source.getPrecipitation(self.index)
					else:
						return ""

				if self.mode == "weathersource":
					return self.source.getVal("source")
				elif self.mode in ("city", "observationpoint"):
					return self.source.getVal("name")
				elif self.mode == "observationtime":
					return self.source.getObservationTime()
				elif self.mode == "sunrise":
					return self.source.getSunrise()
				elif self.mode == "sunset":
					return self.source.getSunset()
				elif self.mode == "isnight":
					return self.source.getIsNight()
				elif self.mode == "temperature_current":
					return self.source.getTemperature()
				elif self.mode == "feelslike":
					return self.source.getFeeltemp()
				elif self.mode == "humidity":
					return self.source.getHumidity()
				elif self.mode == "winddisplay":
					return "%s %s" % (self.source.getWindSpeed(), self.source.getWindDirName())
				elif self.mode == "windspeed":
					return self.source.getWindSpeed()
				elif self.mode == "winddir":
					return self.source.getWindDir()
				elif self.mode == "winddirsign":
					return self.source.getCurrentVal("windDirSign")
				elif self.mode == "winddirarrow":
					return self.source.getCurrentVal("windDirSign").split(" ")[0]
				elif self.mode == "winddirname":
					return self.source.getWindDirName()
				elif self.mode == "winddirshort":
					return self.source.getWindDirShort()
				else:
					return self.source.getVal(self.mode)

			except Exception as err:
				print("[OAWeather] Converter Error:%s" % str(err))
				print_exc()
		return ""

	text = property(getText)

	@cached
	def getIconFilename(self):
		path = ""
		if self.index in (self.CURRENT, self.DAY1, self.DAY2, self.DAY3, self.DAY4, self.DAY5):
			path = self.path
			if path and exists(path):
				code = self.source.getYahooCode(self.index)
				if code:
					path = join(path, "%s.%s" % (code, self.extension))
					if exists(path):
						return path
		self.debug("getIconFilename mode:%s index:%s self.path:%s path:%s" % (self.mode, self.index, self.path, path))
		return path

	def debug(self, text: str):
		if self.enabledebug:
			print("[OAWeather] Converter DEBUG %s" % text)

	iconfilename = property(getIconFilename)
