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

from datetime import datetime
from Components.config import config
from Components.Sources.Source import Source
from Plugins.Extensions.OAWeather.plugin import weatherhandler


class OAWeather(Source):

	YAHOOnightswitch = {
					"3": "47", "4": "47", "11": "45", "12": "45", "13": "46", "14": "46", "15": "46", "16": "46", "28": "27",
					"30": "29", "32": "31", "34": "33", "37": "47", "38": "47", "40": "45", "41": "46", "42": "46", "43": "46"
					}
	METEOnightswitch = {"1": "2", "3": "4", "B": "C", "H": "I", "J": "K"}

	YAHOOdayswitch = {"27": "28", "29": "30", "31": "32", "33": "34", "45": "39", "46": "16", "47": "4"}

	METEOdayswitch = {"2": "1", "3": "4", "C": "B", "I": "H", "K": "J"}

	services = {"MSN": "msn", "OpenMeteo": "omw", "openweather": "owm"}

	def __init__(self):
		Source.__init__(self)
		self.enabledebug = config.plugins.OAWeather.debug.value
		weatherhandler.onUpdate.append(self.callbackUpdate)
		self.data = weatherhandler.getData() or {}
		self.valid = weatherhandler.getValid()
		self.skydirs = weatherhandler.getSkydirs()
		self.na = _("n/a")
		self.tempunit = self.getVal("tempunit")
		self.precipitationtext = "Precipitation"
		self.humiditytext = "Humidity"
		self.feelsliketext = "Feels like"
		self.logo = self.services.get(config.plugins.OAWeather.weatherservice.value, "msn")
		self.pluginpath = None
		self.iconpath = None

	def debug(self, text: str):
		if self.enabledebug:
			print("[OAWeather] Source DEBUG %s" % text)

	def callbackUpdate(self, data):
		self.debug("callbackUpdate: %s" % str(data))
		self.data = data or {}
		self.logo = self.services.get(config.plugins.OAWeather.weatherservice.value, "msn")
		self.tempunit = self.getVal("tempunit")
		self.changed((self.CHANGED_ALL,))

	def getValid(self):
		return self.valid

	def getVal(self, key: str):
		return self.data.get(key, self.na) if self.data else self.na

	def getCurrentVal(self, key: str, default: str = _("n/a")):
		self.debug("getCurrentVal:%s" % key)
		val = self.data.get("current", {}).get(key, default)
		self.debug("current key val: %s" % val)
		return val

	def getObservationTime(self):
		val = self.getCurrentVal("observationTime", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getSunrise(self):
		val = self.getCurrentVal("sunrise", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getDate(self, day: int):
		val = self.getKeyforDay("date", day, "")
		return datetime.fromisoformat(val).strftime("%d. %b") if val else self.na

	def getSunset(self):
		val = self.getCurrentVal("sunset", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getIsNight(self):
		return str(self.getCurrentVal("isNight", "False")) == "True"

	def getTemperature(self):
		return "%s %s" % (self.getCurrentVal("temp"), self.tempunit)

	def getFeeltemp(self, full=False):
		text = "%s " % self.feelsliketext if full else ""
		return "%s%s %s" % (text, self.getCurrentVal("feelsLike"), self.tempunit)

	def getHumidity(self, full=False):
		text = "%s " % self.humiditytext if full else ""
		return "%s%s %s" % (text, self.getCurrentVal("humidity"), "%")

	def getWindSpeed(self):
		return "%s %s" % (self.getCurrentVal("windSpeed"), self.getVal("windunit"))

	def getWindDir(self):
		val = self.getCurrentVal("windDir")
		return ("%s °" % val) if val else self.na

	def getWindDirName(self):
		skydirection = self.getCurrentVal("windDirSign", "")
		if skydirection:
			skydirection = skydirection.split(" ")
			return self.skydirs[skydirection[1]] if skydirection[1] in self.skydirs else skydirection[1]
		else:
			return self.na

	def getWindDirShort(self):
		return self.getCurrentVal("windDirSign", " ").split(" ")[1]

	def getMaxTemp(self, day: int):
		return "%s %s" % (self.getKeyforDay("maxTemp", day), self.tempunit)

	def getMinTemp(self, day: int):
		return "%s %s" % (self.getKeyforDay("minTemp", day), self.tempunit)

	def getMaxMinTemp(self, day: int):
		return "%s / %s %s" % (self.getKeyforDay("minTemp", day), self.getKeyforDay("maxTemp", day), self.tempunit)

	def getPrecipitation(self, day: int, full=False):
		text = "%s " % self.precipitationtext if full else ""
		return "%s%s %s" % (text, self.getKeyforDay("precipitation", day), self.getVal("precunit"))

	def getYahooCode(self, day: int):
		iconcode = self.getKeyforDay("yahooCode", day, "")
		if day == 0 and config.plugins.OAWeather.nighticons.value and self.getIsNight() and iconcode in self.YAHOOnightswitch:
			iconcode = self.YAHOOnightswitch[iconcode]
		else:
			self.YAHOOdayswitch.get(iconcode, iconcode)
		return iconcode

	def getMeteoCode(self, day: int):
		iconcode = self.getKeyforDay("meteoCode", day, "")
		if day == 0 and config.plugins.OAWeather.nighticons.value and self.getIsNight() and iconcode in self.METEOnightswitch:
			iconcode = self.METEOnightswitch[iconcode]
		else:
			self.METEOdayswitch.get(iconcode, iconcode)
		return iconcode

	def getKeyforDay(self, key: str, day: int, default: str = _("n/a")):
		self.debug("getKeyforDay key:%s day:%s default:%s" % (key, day, default))
		if day == 0:
			return self.data.get("current", {}).get(key, default) if self.data else default
		else:
			index = day - 1
			val = self.data.get("forecast", {}).get(index, {}).get(key, default)
			self.debug("getKeyforDay key:%s day:%s / val:%s" % (key, day, val))
			return val

	def destroy(self):
		weatherhandler.onUpdate.remove(self.callbackUpdate)
		Source.destroy(self)
