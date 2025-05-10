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

from datetime import datetime, timedelta
from math import pi, floor, cos
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
		self.pressunit = self.getVal("pressunit")
		self.tempunit = self.getVal("tempunit")
		self.windunit = self.getVal("windunit")
		self.visibilityunit = self.getVal("visibiliyunit")
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
		self.pressunit = self.getVal("pressunit")
		self.tempunit = self.getVal("tempunit")
		self.windunit = self.getVal("windunit")
		self.visibilityunit = self.getVal("visibiliyunit")
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

	def getWeatherSource(self):
		return self.getCurrentVal("source")

	def getCity(self):
		return self.getVal("name")

	def getCityArea(self, default: str = _("n/a")):
		components = self.getCurrentVal("observationPoint").split(", ")
		len_components = len(components)
		if len_components > 1:
			return "%s, %s" % (components[0], components[1])
		if len_components == 1:
			return "%s" % components[0]
		else:
			return default

	def getCityCountry(self, default: str = _("n/a")):
		components = self.getCurrentVal("observationPoint").split(", ")
		len_components = len(components)
		if len_components > 1:
			return "%s, %s" % (components[0], components[1])
		if len_components == 1:
			return "%s" % components[0]
		else:
			return default

	def CityCountryArea(self, default: str = _("n/a")):
		components = self.getCurrentVal("observationPoint").split(", ")
		len_components = len(components)
		if len_components > 2:
			return "%s, %s, %s" % (components[0], components[-1], components[1])
		if len_components == 2:
			return "%s, %s" % (components[0], components[-1])
		if len_components == 1:
			return "%s" % components[0]
		else:
			return default

	def getCityAreaCountry(self):
		return self.getCurrentVal("observationPoint")

	def getObservationTime(self):
		val = self.getCurrentVal("observationTime", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getSunrise(self):
		val = self.getCurrentVal("sunrise", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getSunset(self):
		val = self.getCurrentVal("sunset", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getMoonrise(self):
		val = self.getCurrentVal("moonrise", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getMoonset(self):
		val = self.getCurrentVal("moonset", "")
		return datetime.fromisoformat(val).strftime("%H:%M") if val else self.na

	def getDate(self, day: int):
		val = self.getKeyforDay("date", day, "")
		return datetime.fromisoformat(val).strftime("%d. %b") if val else self.na

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

	def getRainText(self):
		return self.getCurrentVal("raintext", "")

	def getWindSpeed(self):
		windSpeed, windunit = self.getCurrentVal("windSpeed"), self.windunit
		if windunit == "km/h" and config.plugins.OAWeather.windspeedMetricUnit.value == "m/s":
			windSpeed, windunit = str(round(int(windSpeed) / 3.6, 1)), "m/s"
		return "%s %s" % (windSpeed, windunit)

	def getWindDir(self):
		val = self.getCurrentVal("windDir")
		return ("%s °" % val) if val else self.na

	def getWindDirSign(self):
		return self.getCurrentVal("windDirSign", "")

	def getWindDirName(self):
		skydirection = self.getCurrentVal("windDirSign", "* *")
		if skydirection:
			skydirection = skydirection.split(" ")
			return self.skydirs.get(skydirection[1], skydirection[1])
		else:
			return self.na

	def getWindDirArrow(self):
		return self.getCurrentVal("windDirSign", " ").split(" ")[0]

	def getWindDirShort(self):
		return self.getCurrentVal("windDirSign", " ").split(" ")[1]

	def getWindGusts(self):
		windGusts, windunit = self.getCurrentVal("windGusts"), self.windunit
		if windunit == "km/h" and config.plugins.OAWeather.windspeedMetricUnit.value == "m/s":
			windGusts, windunit = str(round(int(windGusts) / 3.6, 1)), "m/s"
		return "%s %s" % (windGusts, windunit)

	def getUVindex(self):
		return self.getCurrentVal("uvIndex", "")

	def getVisibility(self):
		return "%s %s" % (self.getCurrentVal("visibility", self.na), self.visibilityunit)

	def getPressure(self):
		return "%s %s" % (self.getCurrentVal("pressure", self.na), self.pressunit)

	def getAveragePressure(self, day: int):
		return "%s %s" % (self.getKeyforDay("pressure", day), self.pressunit)

	def getMaxTemp(self, day: int):
		return "%s %s" % (self.getKeyforDay("maxTemp", day), self.tempunit)

	def getMinTemp(self, day: int):
		return "%s %s" % (self.getKeyforDay("minTemp", day), self.tempunit)

	def getMaxMinTemp(self, day: int):
		return "%s / %s %s" % (self.getKeyforDay("minTemp", day), self.getKeyforDay("maxTemp", day), self.tempunit)

	def getMaxFeelsLike(self, day: int):
		return "%s %s" % (self.getKeyforDay("maxFeelsLike", day), self.tempunit)

	def getMinFeelsLike(self, day: int):
		return "%s %s" % (self.getKeyforDay("minFeelsLike", day), self.tempunit)

	def getMaxWindSpeed(self, day: int):
		maxwindspeed, windunit = self.getKeyforDay("maxWindSpeed", day), self.windunit
		if windunit == "km/h" and config.plugins.OAWeather.windspeedMetricUnit.value == "m/s":
			maxwindspeed, windunit = str(round(int(maxwindspeed) / 3.6, 1)), "m/s"
		return "%s %s" % (maxwindspeed, windunit)

	def getMinWindSpeed(self, day: int):
		minwindspeed, windunit = self.getKeyforDay("maxWindSpeed", day), self.windunit
		if windunit == "km/h" and config.plugins.OAWeather.windspeedMetricUnit.value == "m/s":
			minwindspeed, windunit = str(round(int(minwindspeed) / 3.6, 1)), "m/s"
		return "%s %s" % (minwindspeed, windunit)

	def getDomWindDir(self, day: int):
		return "%s %s" % (self.getKeyforDay("domWindDir", day), self.tempunit)

	def getDomWindDirSign(self, day: int):
		val = self.getCurrentVal("domWindDirSign")
		return ("%s °" % val) if val else self.na

	def getDomWindDirName(self, day: int):
		skydirection = self.getKeyforDay("domWindDirSign", day)
		if skydirection:
			skydirection = skydirection.split(" ")
			return self.skydirs.get(skydirection[1], skydirection[1])
		else:
			return self.na

	def getDomWindDirArrow(self, day: int):
		return self.getKeyforDay("domWindDirSign", day).split(" ")[0]

	def getDomWindDirShort(self, day: int):
		return self.getKeyforDay("windDirSign", day).split(" ")[1]

	def getMaxWindGusts(self, day: int):
		maxWindGusts, windunit = self.getKeyforDay("maxWindGusts", day), self.windunit
		if windunit == "km/h" and config.plugins.OAWeather.windspeedMetricUnit.value == "m/s":
			maxWindGusts, windunit = str(round(int(maxWindGusts) / 3.6, 1)), "m/s"
		return "%s %s" % (maxWindGusts, windunit)

	def getMaxUvIndex(self, day: int):
		return "%s" % self.getKeyforDay("maxUvIndex", day, "")

	def getMaxVisibility(self, day: int):
		return "%s %s" % (self.getKeyforDay("maxVisibility", day), self.visibilityunit)

	def getPrecipitation(self, day: int, full=False):
		text = "%s " % self.precipitationtext if full else ""
		return "%s%s %s" % (text, self.getKeyforDay("precipitation", day), self.getVal("precunit"))

	def getYahooCode(self, day: int):
		iconcode = self.getKeyforDay("yahooCode", day, "")
		nightSwitch = day == 0 and config.plugins.OAWeather.nighticons.value and self.getIsNight()
		return self.YAHOOnightswitch.get(iconcode, iconcode) if nightSwitch else self.YAHOOdayswitch.get(iconcode, iconcode)

	def getMeteoCode(self, day: int):
		iconcode = self.getKeyforDay("meteoCode", day, "")
		if day == 0 and config.plugins.OAWeather.nighticons.value and self.getIsNight() and iconcode in self.METEOnightswitch:
			iconcode = self.METEOnightswitch[iconcode]
		else:
			self.METEOdayswitch.get(iconcode, iconcode)
		return iconcode

	def getMoonIllumination(self):
		moonIllum = self.moonIllumination(self.moonPosition(datetime.today()))
		if config.plugins.OAWeather.trendarrows.value:
			ta = config.plugins.OAWeather.trendarrows.getText()
			if moonIllum > 0 and ta and len(ta) > 0:
				illumArrow = f"{ta[0]} " if self.moonIllumination(self.moonPosition(datetime.today() - timedelta(hours=1))) < moonIllum else f"{ta[1]} "
			else:
				illumArrow = "● "
		else:
			illumArrow = ""
		return "%s%s %s" % (illumArrow, round(moonIllum, 1), "%")

	def getMoonDistance(self):
		moonDist = self.moonDistance(datetime.today())
		if config.plugins.OAWeather.trendarrows.value:
			ta = config.plugins.OAWeather.trendarrows.getText()
			distArrow = f"{ta[0]} " if self.moonDistance(datetime.today() - timedelta(hours=1)) < moonDist else f"{ta[1]} "
		else:
			distArrow = ""
		return "%s%s %s" % (distArrow, round(moonDist), "km")

	def getMoonPixFilename(self):
		moonPhases = ["new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous", "full_moon", "waning_gibbous", "last_quarter", "waning_crescent"]
		return "%s.png" % moonPhases[self.moonPhase(self.moonPosition(datetime.today()))]

	def moonIllumination(self, pos):
		illum = 100 - abs((cos(pi * pos) + 0j) ** 1.7 * 100)
		return abs(illum - 1) / .99 if illum - 1 > 0 else 0.0

	# Author: Sean B. Palmer, Source: http://inamidst.com/code/moonphase.py
	def moonPosition(self, now=None):
		if now is None:
			now = datetime.today()
		diff = now - datetime(2001, 1, 1)
		days = diff.days + diff.seconds / 86400
		lunations = 0.20439731 + days * 0.03386319269
		return lunations % float(1)

	def moonPhase(self, pos):
		index = (pos * float(8)) + float("0.5")
		index = floor(index)
		return int(index) & 7

	# series expansion of the moon orbital elements from Chapront und Chapront-Touzé
	# Sources: htps://de.wikipedia.org/wiki/Mondbahn, http://articles.adsabs.harvard.edu/full/1994A%26A...282..663S
	def moonDistance(self, now=None):
		if now is None:
			now = datetime.today()
		diff = now - datetime(2000, 1, 1, 12, 0, 0)
		t = diff.days + diff.seconds / 86400
		GM = (134.96341138 + 13.064992953630 * t) * pi / 180
		DD = (297.85020420 + 12.190749117502 * t) * pi / 90
		return 385000.5584 - 20905.3550 * cos(GM) - 3699.1109 * cos(DD - GM) - 2955.9676 * cos(DD) - 569.9251 * cos(2 * GM)

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
