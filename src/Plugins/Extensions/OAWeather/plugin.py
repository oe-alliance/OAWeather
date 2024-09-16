# Copyright (C) 2023 jbleyel, Mr.Servo, Stein17
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

# Some parts are taken from MetrixHD skin and MSNWeather Plugin.

from os import remove, listdir
from os.path import isfile, exists, getmtime, join
from pickle import dump, load
from time import time
from twisted.internet.reactor import callInThread
from xml.etree.ElementTree import tostring, parse
from enigma import eTimer, getDesktop
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigSelectionNumber, ConfigText
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Setup import Setup
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.Directories import SCOPE_CONFIG, SCOPE_PLUGINS, SCOPE_SKINS, resolveFilename
from Tools.Weatherinfo import Weatherinfo
from . import _

config.plugins.OAWeather = ConfigSubsection()
config.plugins.OAWeather.enabled = ConfigYesNo(default=True)

ICONSETS = [("", _("Default"))]
ICONSETROOT = join(resolveFilename(SCOPE_SKINS), "WeatherIconSets")
if exists(ICONSETROOT):
	for iconset in listdir(ICONSETROOT):
		if isfile(join(ICONSETROOT, iconset, "0.png")):
			ICONSETS.append((iconset, iconset))

config.plugins.OAWeather.iconset = ConfigSelection(default="", choices=ICONSETS)
config.plugins.OAWeather.nighticons = ConfigYesNo(default=True)
config.plugins.OAWeather.cachedata = ConfigSelection(default="0", choices=[("0", _("Disabled"))] + [(str(x), _("%d Minutes") % x) for x in (30, 60, 120)])
config.plugins.OAWeather.refreshInterval = ConfigSelectionNumber(0, 1440, 30, default=120, wraparound=True)
config.plugins.OAWeather.apikey = ConfigText(default="", fixed_size=False)
GEODATA = ("Hamburg, DE", "10.000654,53.550341")
config.plugins.OAWeather.weathercity = ConfigText(default=GEODATA[0], visible_width=250, fixed_size=False)
config.plugins.OAWeather.owm_geocode = ConfigText(default=GEODATA[1])
config.plugins.OAWeather.tempUnit = ConfigSelection(default="Celsius", choices=[("Celsius", _("Celsius")), ("Fahrenheit", _("Fahrenheit"))])
config.plugins.OAWeather.weatherservice = ConfigSelection(default="MSN", choices=[("MSN", _("MSN weather")), ("OpenMeteo", _("Open-Meteo Wetter")), ("openweather", _("OpenWeatherMap"))])
config.plugins.OAWeather.debug = ConfigYesNo(default=False)

MODULE_NAME = "OAWeather"
CACHEFILE = resolveFilename(SCOPE_CONFIG, "OAWeather.dat")
PLUGINPATH = join(resolveFilename(SCOPE_PLUGINS), 'Extensions/OAWeather')


class WeatherSettingsView(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "WeatherSettings", plugin="Extensions/OAWeather", PluginLanguageDomain="OAWeather")
		self["key_blue"] = StaticText(_("Location Selection"))
		self["key_yellow"] = StaticText(_("Defaults"))
		self["blueActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keycheckCity, _("Search for your City")),
			"yellow": (self.defaults, _("Set default values"))
		}, prio=0, description=_("Weather Settings Actions"))
		self.old_weatherservice = config.plugins.OAWeather.weatherservice.value
		self.citylist = []
		self.checkcity = False
		self.closeonsave = False

	def keycheckCity(self, closesave=False):
		weathercity = config.plugins.OAWeather.weathercity.value.split(",")[0]
		self["footnote"].setText(_("Search for City ID please wait..."))
		self.closeonsave = closesave
		callInThread(self.searchCity, weathercity)

	def searchCity(self, weathercity):
		services = {"MSN": "msn", "OpenMeteo": "omw", "openweather": "owm"}
		service = services.get(config.plugins.OAWeather.weatherservice.value, "msn")
		apikey = config.plugins.OAWeather.apikey.value
		if service == "owm" and len(apikey) < 32:
			self.session.open(MessageBox, text=_("The API key for OpenWeatherMap is not defined or invalid.\nPlease verify your input data.\nOtherwise your settings won't be saved."), type=MessageBox.TYPE_WARNING)
		else:
			WI = Weatherinfo(service, config.plugins.OAWeather.apikey.value)
			if WI.error:
				print("[WeatherSettingsView] Error in module 'searchCity': %s" % WI.error)
				self["footnote"].setText(_("Error in Weatherinfo"))
				self.session.open(MessageBox, text=WI.error, type=MessageBox.TYPE_ERROR)
			else:
				geodatalist = WI.getCitylist(weathercity, config.osd.language.value.replace('_', '-').lower())
				if WI.error or geodatalist is None or len(geodatalist) == 0:
					print("[WeatherSettingsView] Error in module 'searchCity': %s" % WI.error)
					self["footnote"].setText(_("Error getting City ID"))
					self.session.open(MessageBox, text=_("City '%s' not found! Please try another wording." % weathercity), type=MessageBox.TYPE_WARNING)
#				elif len(geodatalist) == 1:
#					self["footnote"].setText(_("Getting City ID Success"))
#					self.saveGeoCode(geodatalist[0])
				else:
					self.citylist = []
					for item in geodatalist:
						lon = " [lon=%s" % item[1] if float(item[1]) != 0.0 else ""
						lat = ", lat=%s]" % item[2] if float(item[2]) != 0.0 else ""
						try:
							self.citylist.append(("%s%s%s" % (item[0], lon, lat), item[0], item[1], item[2]))
						except Exception:
							print("[WeatherSettingsView] Error in module 'showMenu': faulty entry in resultlist.")
					self.session.openWithCallback(self.choiceIdxCallback, ChoiceBox, titlebartext=_("Select Your Location"), title="", list=tuple(self.citylist))

	def choiceIdxCallback(self, answer):
		if answer is not None:
			self["footnote"].setText(answer[1])
			self.saveGeoCode((answer[1].split(",")[0], answer[2], answer[3]))

	def saveGeoCode(self, value):
		config.plugins.OAWeather.weathercity.value = value[0]
		config.plugins.OAWeather.owm_geocode.value = "%s,%s" % (float(value[1]), float(value[2]))
		self.old_weatherservice = config.plugins.OAWeather.weatherservice.value
		self.checkcity = False
		if self.closeonsave:
			config.plugins.OAWeather.owm_geocode.save()
			weatherhandler.reset()
			Setup.keySave(self)

	def keySelect(self):
		if self.getCurrentItem() == config.plugins.OAWeather.weathercity:
			self.checkcity = True
		Setup.keySelect(self)

	def keySave(self):
		weathercity = config.plugins.OAWeather.weathercity.value.split(",")[0]
		if len(weathercity) < 3:
			self["footnote"].setText(_("The city name is too short. More than 2 characters are needed for search."))
			return
		if self.checkcity or self.old_weatherservice != config.plugins.OAWeather.weatherservice.value:
			self.keycheckCity(True)
			return
		weatherhandler.reset()
		config.plugins.OAWeather.owm_geocode.save()
		Setup.keySave(self)

	def defaults(self, SAVE=False):
		for x in self["config"].list:
			if len(x) > 1:
				self.setInputToDefault(x[1], SAVE)
		self.setInputToDefault(config.plugins.OAWeather.owm_geocode, SAVE)
		if self.session:
			Setup.createSetup(self)

	def setInputToDefault(self, configItem, SAVE):
		configItem.setValue(configItem.default)
		if SAVE:
			configItem.save()


class WeatherHandler():
	def __init__(self):
		self.session = None
		self.enabledebug = config.plugins.OAWeather.debug.value
		modes = {"MSN": "msn", "openweather": "owm", "OpenMeteo": "omw"}
		mode = modes.get(config.plugins.OAWeather.weatherservice.value, "msn")
		self.WI = Weatherinfo(mode, config.plugins.OAWeather.apikey.value)
		self.geocode = config.plugins.OAWeather.owm_geocode.value.split(",")
		self.weathercity = None
		self.trialcounter = 0
		self.currentWeatherDataValid = 3  # 0= green (data available), 1= yellow (still working), 2= red (no data available, wait on next refresh) 3=startup
		self.refreshTimer = eTimer()
		self.refreshTimer.callback.append(self.refreshWeatherData)
		self.wetterdata = None
		self.onUpdate = []
		self.skydirs = {"N": _("North"), "NE": _("Northeast"), "E": _("East"), "SE": _("Southeast"), "S": _("South"), "SW": _("Southwest"), "W": _("West"), "NW": _("Northwest")}
		self.msnFullData = None

	def sessionStart(self, session):
		self.session = session
		self.debug("sessionStart")
		self.getCacheData()

	def writeData(self, data):
		self.debug("writeData")
		self.currentWeatherDataValid = 0
		self.wetterdata = data
		for callback in self.onUpdate:
			callback(data)

		seconds = int(config.plugins.OAWeather.refreshInterval.value * 60)
		self.refreshTimer.start(seconds * 1000, True)

	def getData(self):
		return self.wetterdata

	def getValid(self) -> int:
		return self.currentWeatherDataValid

	def getSkydirs(self) -> dict:
		return self.skydirs

	def getCacheData(self):
		cacheminutes = int(config.plugins.OAWeather.cachedata.value)
		if cacheminutes and isfile(CACHEFILE):
			timedelta = (time() - getmtime(CACHEFILE)) / 60
			if cacheminutes > timedelta:
				with open(CACHEFILE, "rb") as fd:
					cache_data = load(fd)
				self.writeData(cache_data)
				return

		self.refreshTimer.start(3000, True)

	def refreshWeatherData(self, entry=None):
		self.debug("refreshWeatherData")
		self.refreshTimer.stop()
		if config.misc.firstrun.value:  # don't refresh on firstrun try again after 10 seconds
			self.debug("firstrun")
			self.refreshTimer.start(600000, True)
			return
		if config.plugins.OAWeather.enabled.value:
			self.weathercity = config.plugins.OAWeather.weathercity.value
			geocode = config.plugins.OAWeather.owm_geocode.value.split(",")
			# DEPRECATED, will be removed in April 2023
			if geocode == ['0.0', '0.0']:
				geodatalist = self.WI.getCitylist(config.plugins.OAWeather.weathercity.value.split(",")[0], config.osd.language.value.replace('_', '-').lower())
				if geodatalist is not None and len(geodatalist[0]) == 3:
					geocode = [geodatalist[0][1], geodatalist[0][2]]
					config.plugins.OAWeather.weathercity.value = geodatalist[0][0]
					config.plugins.OAWeather.weathercity.save()
					config.plugins.OAWeather.owm_geocode.value = "%s,%s" % (float(geocode[0]), float(geocode[1]))
					config.plugins.OAWeather.owm_geocode.save()
			# DEPRECATED, will be removed in April 2023
			if geocode and len(geocode) == 2:
				geodata = (self.weathercity, geocode[0], geocode[1])  # tuple ("Cityname", longitude, latitude)
			else:
				geodata = None
			language = config.osd.language.value.replace("_", "-")
			unit = "imperial" if config.plugins.OAWeather.tempUnit.value == "Fahrenheit" else "metric"
			if geodata:
				self.WI.start(geodata=geodata, cityID=None, units=unit, scheme=language, reduced=True, callback=self.refreshWeatherDataCallback)
			else:
				print("[%s] error in OAWeather config" % (MODULE_NAME))
				self.currentWeatherDataValid = 2

	def refreshWeatherDataCallback(self, data, error):
		self.debug("refreshWeatherDataCallback")
		if error or data is None:
			self.trialcounter += 1
			if self.trialcounter < 2:
				print("[%s] lookup for city '%s' paused, try again in 10 secs..." % (MODULE_NAME, self.weathercity))
				self.currentWeatherDataValid = 1
				self.refreshTimer.start(10000, True)
			elif self.trialcounter > 5:
				print("[%s] lookup for city '%s' paused 1 h, to many errors..." % (MODULE_NAME, self.weathercity))
				self.currentWeatherDataValid = 2
				self.refreshTimer.start(3600000, True)
			else:
				print("[%s] lookup for city '%s' paused 5 mins, to many errors..." % (MODULE_NAME, self.weathercity))
				self.currentWeatherDataValid = 2
				self.refreshTimer.start(300000, True)
			return
		self.writeData(data)
		self.msnFullData = self.WI.info if config.plugins.OAWeather.weatherservice.value == "MSN" else None
		# TODO write cache only on close
		if config.plugins.OAWeather.cachedata.value != "0":
			with open(CACHEFILE, "wb") as fd:
				dump(data, fd, -1)

	def reset(self):
		self.refreshTimer.stop()
		if isfile(CACHEFILE):
			remove(CACHEFILE)
		modes = {"MSN": "msn", "openweather": "owm", "OpenMeteo": "omw"}
		mode = modes.get(config.plugins.OAWeather.weatherservice.value, "msn")
		self.WI.setmode(mode, config.plugins.OAWeather.apikey.value)
		if self.WI.error:
			print(self.WI.error)
			self.WI.setmode()  # fallback to MSN

		if self.session:
			iconpath = config.plugins.OAWeather.iconset.value
			iconpath = join(ICONSETROOT, iconpath) if iconpath else join(PLUGINPATH, "Icons")
			self.session.screen["OAWeather"].iconpath = iconpath
		self.refreshWeatherData()

	def debug(self, text: str):
		if self.enabledebug:
			print("[%s] WeatherHandler DEBUG %s" % (MODULE_NAME, text))


def main(session, **kwargs):
	session.open(OAWeatherPlugin)


def setup(session, **kwargs):
	session.open(WeatherSettingsView)


def sessionstart(session, **kwargs):
	from Components.Sources.OAWeather import OAWeather
	session.screen["OAWeather"] = OAWeather()
	session.screen["OAWeather"].precipitationtext = _("Precipitation")
	session.screen["OAWeather"].humiditytext = _("Humidity")
	session.screen["OAWeather"].feelsliketext = _("Feels like")
	session.screen["OAWeather"].pluginpath = PLUGINPATH
	iconpath = config.plugins.OAWeather.iconset.value
	if iconpath:
		iconpath = join(ICONSETROOT, iconpath)
	else:
		iconpath = join(PLUGINPATH, "Icons")
	session.screen["OAWeather"].iconpath = iconpath
	weatherhandler.sessionStart(session)


def Plugins(**kwargs):
	pluginList = []
	pluginList.append(PluginDescriptor(name="OAWeather", where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart, needsRestart=False))
	pluginList.append(PluginDescriptor(name="Weather Plugin", description=_("Show Weather Forecast"), icon="plugin.png", where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=main))
	return pluginList


class OAWeatherPlugin(Screen):
	def __init__(self, session):
		params = {
			"picpath": join(PLUGINPATH, "Images")
		}
		skintext = ""
		xmlFile = join(PLUGINPATH, "skin_FHD.xml") if getDesktop(0).size().height() == 1080 else ""
		if not exists(xmlFile):
			xmlFile = join(PLUGINPATH, "skin.xml")
		xml = parse(xmlFile).getroot()
		for screen in xml.findall('screen'):
			if screen.get("name") == "OAWeatherPlugin":
				skintext = tostring(screen).decode()
				for key in params.keys():
					try:
						skintext = skintext.replace('{%s}' % key, params[key])
					except Exception as e:
						print("%s@key=%s" % (str(e), key))
				break
		self.skin = skintext
		Screen.__init__(self, session)
		self.title = _("Weather Plugin")
		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
		{
			"cancel": self.close,
			"menu": self.config,
		}, -1)

		self["statustext"] = StaticText()
		self["update"] = Label(_("Update"))
		self["current"] = Label(_("Current Weather"))
		self["today"] = Label(_("Today"))

		for i in range(1, 6):
			self["weekday%s_temp" % i] = StaticText()

		self.data = None
		self.na = _("n/a")

		self.onLayoutFinish.append(self.startRun)

	def startRun(self):
		self.data = weatherhandler.getData() or {}
		if self.data:
			self.getWeatherDataCallback()

	def clearFields(self):
		for i in range(1, 6):
			self["weekday%s_temp" % i].text = ""

	def getVal(self, key: str):
		return self.data.get(key, self.na) if self.data else self.na

	def getCurrentVal(self, key: str, default: str = _("n/a")):
		value = default
		if self.data and "current" in self.data:
			current = self.data.get("current", {})
			if key in current:
				value = current.get(key, default)
		return value

	def getWeatherDataCallback(self):
		self["statustext"].text = ""
		forecast = self.data.get("forecast")
		tempunit = self.data.get("tempunit", self.na)
		for day in range(1, 6):
			item = forecast.get(day)
			lowTemp = item.get("minTemp")
			highTemp = item.get("maxTemp")
			text = item.get("text")
			self["weekday%s_temp" % day].text = "%s %s|%s %s\n%s" % (highTemp, tempunit, lowTemp, tempunit, text)

	def config(self):
		self.session.openWithCallback(self.setupFinished, WeatherSettingsView)

	def setupFinished(self, result=None):
		self.clearFields()
		self.startRun()

	def error(self, errortext):
		self.clearFields()
		self["statustext"].text = errortext


weatherhandler = WeatherHandler()
