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

from os.path import join, exists, isfile
from traceback import print_exc

from Components.Converter.Converter import Converter
from Components.config import config
from Components.Element import cached


class OAWeather(Converter, object):
	CURRENT = 0
	DAY1 = 1
	DAY2 = 2
	DAY3 = 3
	DAY4 = 4
	DAY5 = 5
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
		self.logo = None
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
					if self.mode == "pressure_average":
						return self.source.getAveragePressure(self.index)
					elif self.mode == "temperature_high":
						return self.source.getMaxTemp(self.index)
					elif self.mode == "temperature_low":
						return self.source.getMinTemp(self.index)
					elif self.mode == "temperature_high_low":
						return self.source.getMaxMinTemp(self.index)
					elif self.mode == "temperature_text":
						return self.source.getKeyforDay("text", self.index, "")
					elif self.mode == "feelslike_max":
						return "%s %s" % (self.source.getMaxFeelsLike(self.index))
					elif self.mode == "feelslike_min":
						return "%s %s" % (self.source.getMinFeelsLike(self.index))
					elif self.mode == "winddisplay_max":
						return "%s %s" % (self.source.getMaxWindSpeed(self.index), self.source.getDomWindDirName(self.index))
					elif self.mode == "windspeed_max":
						return self.source.getMaxWindSpeed(self.index)
					elif self.mode == "winddir_dominant":
						return self.source.getDomWindDir(self.index)
					elif self.mode == "winddirsign_dominant":
						return self.source.getDomWindDirSign(self.index)
					elif self.mode == "winddirarrow_dominant":
						return self.source.getDomWindDirArrow(self.index)
					elif self.mode == "winddirname_dominant":
						return self.source.getDomWindDirName(self.index)
					elif self.mode == "winddirshort_dominant":
						return self.source.getDomWindDirShort(self.index)
					elif self.mode == "windgusts_max":
						return self.source.getMaxWindGusts(self.index)
					elif self.mode == "uvindex_max":
						return self.source.getMaxUvIndex(self.index)
					elif self.mode == "visibility_max":
						return self.source.getMaxVisibility(self.index)
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
					elif self.mode == "precipitationfull":
						return self.source.getPrecipitation(self.index, True)
					else:
						return self.source.getKeyforDay(self.mode, self.index, "")
				if self.mode == "weathersource":
					return self.source.getWeatherSource()
				elif self.mode == "city":
					return self.source.getCity()
				elif self.mode == "cityarea":
					return self.source.getCityArea()
				elif self.mode == "citycountry":
					return self.source.CityCountry()
				elif self.mode == "citycountryarea":
					return self.source.CityCountryArea()
				elif self.mode in ["cityareacountry", "observationPoint"]:
					return self.source.getCityAreaCountry()
				elif self.mode == "observationtime":
					return self.source.getObservationTime()
				elif self.mode == "sunrise":
					return self.source.getSunrise()
				elif self.mode == "sunset":
					return self.source.getSunset()
				elif self.mode == "moonrise":
					return self.source.getMoonrise()
				elif self.mode == "moonset":
					return self.source.getMoonset()
				elif self.mode == "isnight":
					return self.source.getIsNight()
				elif self.mode == "pressure_current":
					return self.source.getPressure()
				elif self.mode == "temperature_current":
					return self.source.getTemperature()
				elif self.mode == "feelslike":
					return self.source.getFeeltemp()
				elif self.mode == "feelslikefull":
					return self.source.getFeeltemp(True)
				elif self.mode == "humidity":
					return self.source.getHumidity()
				elif self.mode == "humidityfull":
					return self.source.getHumidity(True)
				elif self.mode == "raintext":
					return self.source.getRainText()
				elif self.mode == "winddisplay":
					return "%s %s" % (self.source.getWindSpeed(), self.source.getWindDirName())
				elif self.mode == "windspeed":
					return self.source.getWindSpeed()
				elif self.mode == "winddir":
					return self.source.getWindDir()
				elif self.mode == "winddirsign":
					return self.source.getWindDirsign()
				elif self.mode == "winddirarrow":
					return self.source.getWindDirArrow()
				elif self.mode == "winddirname":
					return self.source.getWindDirName()
				elif self.mode == "winddirshort":
					return self.source.getWindDirShort()
				elif self.mode == "windgusts":
					return self.source.getWindGusts()
				elif self.mode == "uvindex":
					return self.source.getUVindex()
				elif self.mode == "visibility":
					return self.source.getVisibility()
				elif self.mode == "moonillumination":
					return self.source.getMoonIllumination()
				elif self.mode == "moondistance":
					return self.source.getMoonDistance()
				elif self.mode == "moonphaseicon":
					return self.source.getMoonPixFilename()
				else:
					return self.source.getVal(self.mode)
			except Exception as err:
				print("[OAWeather] Converter Error:%s" % str(err))
				print_exc()
		return ""

	text = property(getText)

	@cached
	def getBoolean(self):
		if self.mode == "isnight":
			return self.source.getIsNight()
		elif self.mode == "raintext":
			return self.source.getRainText() != ""
		elif self.mode == "uvindex":
			return self.source.getUVindex() != ""
		elif self.mode in ("daySummary0", "nightSummary0"):
			return self.source.getKeyforDay(self.mode, self.index, "") != ""
		else:
			return False

	boolean = property(getBoolean)

	@cached
	def getIconFilename(self):
		if self.mode == "logo":
			try:
				path = join(self.source.pluginpath, "Images", "%s_weather_logo.png" % self.source.logo)
				if isfile(path):
					return path
			except Exception:
				return ""
		if self.mode == "moonphaseicon":
			try:
				path = join(self.source.pluginpath, "Images/moonphases/", self.source.getMoonPixFilename())
				if isfile(path):
					return path
			except Exception:
				return ""
		if self.index in (self.CURRENT, self.DAY1, self.DAY2, self.DAY3, self.DAY4, self.DAY5):
			path = self.source.iconpath
			if self.path:
				path = self.path
			if path and exists(path):
				code = self.source.getYahooCode(self.index)
				if code:
					path = join(path, "%s.%s" % (code, self.extension))
					if isfile(path):
						return path
			self.debug("getIconFilename not found mode:%s index:%s self.path:%s path:%s" % (self.mode, self.index, self.path, path))
		return ""

	iconfilename = property(getIconFilename)

	def debug(self, text: str):
		if self.enabledebug:
			print("[OAWeather] Converter DEBUG %s" % text)
