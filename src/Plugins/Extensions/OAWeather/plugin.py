# Copyright (C) 2025 jbleyel, Mr.Servo, Stein17
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
# mod by lululla 20250629
# -fix asiatic language and icons 20250706 (use mod on converter tools
# -refactory favoritelist

from datetime import datetime, timedelta
from os import remove, listdir, chmod, replace
from os.path import isfile, exists, getmtime, join
from pickle import dump, load
from time import time
from twisted.internet.reactor import callInThread
from xml.etree.ElementTree import tostring, parse
from enigma import eTimer, addFont
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigSelectionNumber, ConfigText, configfile
from Components.Label import Label
from Components.Sources.List import List
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import SCOPE_CONFIG, SCOPE_PLUGINS, SCOPE_SKINS, SCOPE_FONTS, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.Weatherinfo import Weatherinfo

from . import __version__, _


class WeatherHelper():
    def __init__(self):
        self.version = __version__
        self.favoritefile = resolveFilename(SCOPE_CONFIG, "oaweather_fav.dat")
        # self.favoritefile = resolveFilename(SCOPE_CONFIG, "oaweather_fav.json")  # Cambiato da .dat a .json
        self.locationDefault = ("Hamburg, DE", 10.00065, 53.55034)
        self.favoriteList = []

    # add from lululla
    def addFavorite(self, location):
        if location not in self.favoriteList:
            self.favoriteList.append(location)
            self.syncWithConfig()
            self.saveFavorites()

    def syncWithConfig(self):
        current_city = config.plugins.OAWeather.weathercity.value
        current_geocode = config.plugins.OAWeather.owm_geocode.value
        if current_city and current_geocode and current_city != self.locationDefault[0]:
            try:
                lon, lat = current_geocode.split(",")
                location = (current_city, float(lon), float(lat))
                if location not in self.favoriteList:
                    self.addFavorite(location)
                config.plugins.OAWeather.weatherlocation.value = location
                config.plugins.OAWeather.weatherlocation.save()
            except Exception as e:
                print(f"Error syncing config: {str(e)}")

    def saveFavorites(self):
        """Improved version but with the same name for compatibility"""
        try:

            temp_file = "%s.tmp" % self.favoritefile
            with open(temp_file, "wb") as f:
                dump(self.favoriteList, f, -1)
            replace(temp_file, self.favoritefile)
            chmod(self.favoritefile, 0o644)

            return True

        except Exception as e:
            print("Main save error: %s" % str(e))

            try:
                fallback = resolveFilename(SCOPE_CONFIG, "oaweather_fav.dat")
                with open(fallback, "w", encoding="utf-8") as f:
                    dump(self.favoriteList, f, indent=2, ensure_ascii=False)
                print("Fallback used: %s" % fallback)
                return True
            except Exception as fallback_error:
                print("Fallback error: %s" % str(fallback_error))
                return False


    def readFavoriteList(self):
        if exists(self.favoritefile):
            try:
                with open(self.favoritefile, "rb") as file:
                    self.favoriteList = load(file)
            except:
                self.favoriteList = [self.locationDefault]
                self.saveFavorites()
        else:
            self.favoriteList = [self.locationDefault]
            self.saveFavorites()

    # end add lululla

    def setFavoriteList(self, favoriteList):
        self.favoriteList = favoriteList

    def reduceCityname(self, weathercity):
        components = list(dict.fromkeys(weathercity.split(', ')))  # remove duplicates from list
        len_components = len(components)
        if len_components > 2:
            return (f"{components[0]}, {components[1]}, {components[-1]}")
        return (f"{components[0]}, {components[1]}") if len_components == 2 else (f"{components[0]}")

    def isolateCityname(self, weathercity):
        return weathercity.split(",")[0]

    def isDifferentLocation(self, geodata1, geodata2):
        return ((geodata1[1] - geodata2[1])**2 + (geodata1[2] - geodata2[2])**2)**.5 > 0.02

    def convertOldLocation(self):  # deprecated: will be removed at end of 2025
        if config.plugins.OAWeather.owm_geocode.value and config.plugins.OAWeather.weathercity.value:
            if config.plugins.OAWeather.weatherlocation.value == config.plugins.OAWeather.weatherlocation.default:
                weathercity = config.plugins.OAWeather.weathercity.value
                lon, lat = eval(str(config.plugins.OAWeather.owm_geocode.value))
                config.plugins.OAWeather.weatherlocation.value = (weathercity, lon, lat)
                config.plugins.OAWeather.weatherlocation.save()
            # remove old entries from '/etc/enigma2/settings'
            config.plugins.OAWeather.owm_geocode.value = config.plugins.OAWeather.owm_geocode.default
            config.plugins.OAWeather.owm_geocode.save()
            config.plugins.OAWeather.weathercity.value = config.plugins.OAWeather.weathercity.default
            config.plugins.OAWeather.weathercity.save()

    def loadSkin(self, skinName=""):
        params = {"picpath": join(PLUGINPATH, "Images")}
        skintext = ""
        xml = parse(join(PLUGINPATH, "skin.xml")).getroot()
        for screen in xml.findall('screen'):
            if screen.get("name") == skinName:
                skintext = tostring(screen).decode()
                for key in params.keys():
                    try:
                        skintext = skintext.replace('{%s}' % key, params[key])
                    except Exception as e:
                        print("%s@key=%s" % (str(e), key))
                break
        return skintext


weatherhelper = WeatherHelper()


config.plugins.OAWeather = ConfigSubsection()
ICONSETS = [("", _("Default"))]
ICONSETROOT = join(resolveFilename(SCOPE_SKINS), "WeatherIconSets")
if exists(ICONSETROOT):
    for iconset in listdir(ICONSETROOT):
        if isfile(join(ICONSETROOT, iconset, "0.png")):
            ICONSETS.append((iconset, iconset))
config.plugins.OAWeather.enabled = ConfigYesNo(default=True)
config.plugins.OAWeather.iconset = ConfigSelection(default="", choices=ICONSETS)
config.plugins.OAWeather.nighticons = ConfigYesNo(default=True)
config.plugins.OAWeather.cachedata = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + [(x, _("%d Minutes") % x) for x in (30, 60, 120)])
config.plugins.OAWeather.refreshInterval = ConfigSelectionNumber(0, 1440, 30, default=120, wraparound=True)
config.plugins.OAWeather.apikey = ConfigText(default="", fixed_size=False)
config.plugins.OAWeather.weathercity = ConfigText(default="", visible_width=250, fixed_size=False)  # deprecated: will be removed at end of 2025
config.plugins.OAWeather.owm_geocode = ConfigText(default=(0, 0))  # deprecated: will be removed at end of 2025
weatherhelper.readFavoriteList()
choiceList = [(item, item[0]) for item in weatherhelper.favoriteList]
config.plugins.OAWeather.weatherlocation = ConfigSelection(default=weatherhelper.locationDefault, choices=choiceList)
weatherhelper.convertOldLocation()  # deprecated: will be removed at end of 2025
config.plugins.OAWeather.detailLevel = ConfigSelection(default="default", choices=[("default", _("More Details / Smaller font")), ("reduced", _("Less details / Larger font"))])
config.plugins.OAWeather.tempUnit = ConfigSelection(default="Celsius", choices=[("Celsius", _("Celsius")), ("Fahrenheit", _("Fahrenheit"))])
config.plugins.OAWeather.windspeedMetricUnit = ConfigSelection(default="km/h", choices=[("km/h", _("km/h")), ("m/s", _("m/s"))])
config.plugins.OAWeather.trendarrows = ConfigSelection(default=1, choices=[(0, _("Disabled")), (1, "▲▼"), (2, "∆∇"), (3, "↑↓"), (4, "↥↧"), (5, "⇧⇩"), (6, "⇑⇓"), (7, "∧∨"), (8, "<>"), (9, "+-")])
config.plugins.OAWeather.weatherservice = ConfigSelection(default="MSN", choices=[("MSN", _("MSN weather")), ("OpenMeteo", _("Open-Meteo Wetter")), ("openweather", _("OpenWeatherMap"))])
config.plugins.OAWeather.debug = ConfigYesNo(default=False)

MODULE_NAME = "OAWeather"
CACHEFILE = resolveFilename(SCOPE_CONFIG, "OAWeather.dat")
PLUGINPATH = join(resolveFilename(SCOPE_PLUGINS), 'Extensions/OAWeather')

fontFile = resolveFilename(SCOPE_FONTS, "fallback.font")
if isfile(fontFile):
<<<<<<< Updated upstream
	addFont(fontFile, "OAWeatherFont", 100, -1, 0)
=======
    addFont(fontFile, "OAWeatherFont", 100, -1, 0)
>>>>>>> Stashed changes
elif config.plugins.OAWeather.debug.value:
    print("[%s] OAWeatherDetailview__init__: %s" % (MODULE_NAME, fontFile))


class WeatherSettingsView(Setup):
    def __init__(self, session):
        Setup.__init__(self, session, "WeatherSettings", plugin="Extensions/OAWeather", PluginLanguageDomain="OAWeather")
        self["key_blue"] = StaticText(_("Manage favorites"))
        self["key_yellow"] = StaticText(_("Defaults"))
        self["blueActions"] = HelpableActionMap(self, ["ColorActions"], {
            "yellow": (self.keyYellow, _("Set default values")),
            "blue": (self.keyBlue, _("Search for your city")),
            }, prio=0, description=_("Weather Settings Actions"))
        self.old_weatherservice = config.plugins.OAWeather.weatherservice.value
        self.old_weatherlocation = config.plugins.OAWeather.weatherlocation.value

    def keySelect(self):
        if self.getCurrentItem() == config.plugins.OAWeather.weatherlocation.value:
            self.session.openWithCallback(self.returnKeySelect, OAWeatherFavorites)
        else:
            Setup.keySelect(self)

    def returnKeySelect(self, weatherLocation):
        if weatherLocation is not None and weatherLocation != self.old_weatherlocation:
            weatherhandler.reset()
        Setup.keySelect(self)

<<<<<<< Updated upstream
	def keySave(self):
		weathercity = config.plugins.OAWeather.weatherlocation.value[0]
		if len(weathercity) < 3:
			self["footnote"].setText(_("The city name is too short. More than 2 characters are needed for search."))
			return
		if self.old_weatherservice != config.plugins.OAWeather.weatherservice.value:
			config.plugins.OAWeather.weatherservice.save()
			weatherhandler.reset()
		if self.old_weatherlocation != config.plugins.OAWeather.weatherlocation.value:
			config.plugins.OAWeather.weatherlocation.save()
			weatherhandler.reset(newLocation=config.plugins.OAWeather.weatherlocation.value)
		if config.plugins.OAWeather.trendarrows.isChanged():
			self.session.screen["OAWeather"].changed((1,))  # (1,) = refresh all source widgets
		Setup.keySave(self)
=======
    def keySave(self):
        weathercity = config.plugins.OAWeather.weatherlocation.value[0]
        if len(weathercity) < 3:
            self["footnote"].setText(_("The city name is too short. More than 2 characters are needed for search."))
            return
        if self.old_weatherservice != config.plugins.OAWeather.weatherservice.value:
            config.plugins.OAWeather.weatherservice.save()
            weatherhandler.reset()
        if self.old_weatherlocation != config.plugins.OAWeather.weatherlocation.value:
            config.plugins.OAWeather.weatherlocation.save()
            weatherhandler.reset(newLocation=config.plugins.OAWeather.weatherlocation.value)
        if config.plugins.OAWeather.trendarrows.isChanged():
            self.session.screen["OAWeather"].changed((1,))  # (1,) = refresh all source widgets
        Setup.keySave(self)
>>>>>>> Stashed changes

    def keyYellow(self, SAVE=False):
        for x in self["config"].list:
            if len(x) > 1:
                self.setInputToDefault(x[1], SAVE)
        self.setInputToDefault(config.plugins.OAWeather.weatherlocation, SAVE)
        if self.session:
            Setup.createSetup(self)

    #edit lululla
    def keyBlue(self):
        self.session.openWithCallback(self.returnFavoriteSelection, OAWeatherFavorites)

    def returnFavoriteSelection(self, selected_favorite):
        if selected_favorite is not None:
            config.plugins.OAWeather.weatherlocation.value = selected_favorite
            weatherhandler.reset(newLocation=selected_favorite)
    #and edit lululla

    def setInputToDefault(self, configItem, SAVE):
        configItem.setValue(configItem.default)
        if SAVE:
            configItem.save()


class WeatherHandler():
    def __init__(self):
        self.session = None
        self.enabledebug = config.plugins.OAWeather.debug.value
        mode = {"MSN": "msn", "OpenMeteo": "omw", "openweather": "owm"}.get(config.plugins.OAWeather.weatherservice.value, "msn")
        self.WI = Weatherinfo(mode, config.plugins.OAWeather.apikey.value)
        self.currCity = ""
        self.currLocation = config.plugins.OAWeather.weatherlocation.value
        self.trialcounter = 0
        self.currentWeatherDictValid = 3  # 0= green (data available), 1= yellow (still working), 2= red (no data available, wait on next refresh) 3=startup
        self.refreshTimer = eTimer()
        self.refreshTimer.callback.append(self.refreshWeatherData)
        self.weatherDict = {}
        self.fullWeatherDict = {}
        self.onUpdate = []
        self.refreshCallback = None
        self.skydirs = {"N": _("North"), "NE": _("Northeast"), "E": _("East"), "SE": _("Southeast"), "S": _("South"), "SW": _("Southwest"), "W": _("West"), "NW": _("Northwest")}

    def sessionStart(self, session):
        self.session = session
        self.debug("sessionStart")
        self.getCacheData()

    def writeData(self, data):
        self.debug("writeData")
        self.currentWeatherDictValid = 0
        self.weatherDict = data
        for callback in self.onUpdate:
            callback(data)
        seconds = int(config.plugins.OAWeather.refreshInterval.value * 60)
        self.refreshTimer.start(seconds * 1000, True)

    def getData(self):
        return self.weatherDict

    def getFulldata(self):
        return self.fullWeatherDict

    def getValid(self) -> int:
        return self.currentWeatherDictValid

    def getSkydirs(self) -> dict:
        return self.skydirs

    def getCacheData(self):
        cacheminutes = config.plugins.OAWeather.cachedata.value
        if cacheminutes and isfile(CACHEFILE):
            timedelta = (time() - getmtime(CACHEFILE)) / 60
            if cacheminutes > timedelta:
                with open(CACHEFILE, "rb") as fd:
                    cache_data = load(fd)
                self.writeData(cache_data)
                return
        self.refreshTimer.start(3000, True)

    def getCurrLocation(self):
        return self.currLocation

    def setCurrLocation(self, currLocation):
        self.currLocation = currLocation

    def refreshWeatherData(self, entry=None):
        self.debug("refreshWeatherData")
        self.refreshTimer.stop()
        if config.misc.firstrun.value:  # don't refresh on firstrun try again after 10 seconds
            self.debug("firstrun")
            self.refreshTimer.start(600000, True)
            return
        if config.plugins.OAWeather.enabled.value:
            self.currCity = weatherhelper.isolateCityname(self.currLocation[0])
            language = config.osd.language.value.replace("_", "-")
            unit = "imperial" if config.plugins.OAWeather.tempUnit.value == "Fahrenheit" else "metric"
            if self.currLocation:
                self.WI.start(geodata=self.currLocation, units=unit, scheme=language, reduced=True, callback=self.refreshWeatherDataCallback)
            else:
                print("[%s] error in OAWeather config" % (MODULE_NAME))
                self.currentWeatherDictValid = 2

    def refreshWeatherDataCallback(self, data, error):
        self.debug("refreshWeatherDataCallback")
        if error or data is None:
            self.trialcounter += 1
            if self.trialcounter < 2:
                print("[%s] lookup for city '%s' paused, try again in 10 secs..." % (MODULE_NAME, self.currCity))
                self.currentWeatherDictValid = 1
                self.refreshTimer.start(10000, True)
            elif self.trialcounter > 5:
                print("[%s] lookup for city '%s' paused 1 h, to many errors..." % (MODULE_NAME, self.currCity))
                self.currentWeatherDictValid = 2
                self.refreshTimer.start(3600000, True)
            else:
                print("[%s] lookup for city '%s' paused 5 mins, to many errors..." % (MODULE_NAME, self.currCity))
                self.currentWeatherDictValid = 2
                self.refreshTimer.start(300000, True)
            return
        self.writeData(data)
        self.fullWeatherDict = self.WI.info
        # TODO write cache only on close
        if config.plugins.OAWeather.cachedata.value and self.currLocation == config.plugins.OAWeather.weatherlocation.value:
            with open(CACHEFILE, "wb") as fd:
                dump(data, fd, -1)
        if self.refreshCallback:
            self.refreshCallback()
            self.refreshCallback = None

    def reset(self, newLocation=None, callback=None):
        self.refreshCallback = callback
        if newLocation:
            self.currLocation = newLocation
        self.refreshTimer.stop()
        if isfile(CACHEFILE):
            remove(CACHEFILE)
        mode = {"MSN": "msn", "OpenMeteo": "omw", "openweather": "owm"}.get(config.plugins.OAWeather.weatherservice.value, "msn")
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
    session.open(OAWeatherOverview)


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


class OAWeatherOverview(Screen):
    def __init__(self, session):
        self.session = session
        self.skin = weatherhelper.loadSkin("OAWeatherOverview")
        Screen.__init__(self, session)
        weatherLocation = config.plugins.OAWeather.weatherlocation.value
        if weatherLocation != weatherhandler.getCurrLocation():
            weatherhandler.setCurrLocation(weatherLocation)
            weatherhandler.refreshWeatherData()
        self.currFavIdx = weatherhelper.favoriteList.index(weatherLocation) if weatherLocation in weatherhelper.favoriteList else 0
        self.data = {}
        self.na = _("n/a")
        self.title = _("Weather Plugin Overview")
        self["version"] = StaticText(f"OA-Weather {__version__}")
        self["statustext"] = StaticText()
        self["update"] = Label(_("Update"))
        self["current"] = Label(_("Current Weather"))
        self["today"] = StaticText(_("Today"))
        self["key_red"] = StaticText(_("Exit"))
        self["key_green"] = StaticText(_("Chose favorite"))
        self["key_yellow"] = StaticText(_("Previous favorite"))
        self["key_blue"] = StaticText(_("Next favorite"))
        self["key_ok"] = StaticText(_("View details"))
        self["key_menu"] = StaticText(_("Settings"))
        self["actions"] = ActionMap(["OAWeatherActions",
                                    "ColorActions",
                                    "InfoActions"], {
                                                    "ok": self.keyOk,
                                                    "cancel": self.close,
                                                    "red": self.close,
                                                    "yellow": self.favoriteUp,
                                                    "blue": self.favoriteDown,
                                                    "green": self.favoriteChoice,
                                                    "menu": self.config,
                                                    "info": self.keyOk
                                                    }, -1)
        for idx in range(1, 6):
            self[f"weekday{idx}_temp"] = StaticText()
        self.onLayoutFinish.append(self.startRun)

    def startRun(self):
        self.data = weatherhandler.getData() or {}
        if self.data:
            self.getWeatherDataCallback()

    def clearFields(self):
        for idx in range(1, 6):
            self[f"weekday{idx}_temp"].text = ""

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
        forecast = self.data.get("forecast", {})
        tempunit = self.data.get("tempunit", self.na)
        for day in range(1, 6):
            item = forecast.get(day, {})
            lowTemp = item.get("minTemp", "")
            highTemp = item.get("maxTemp", "")
            text = item.get("text", "")
            self[f"weekday{day}_temp"].text = "%s %s|%s %s\n%s" % (highTemp, tempunit, lowTemp, tempunit, text)

    def keyOk(self):
        if weatherhelper.favoriteList and weatherhandler.WI.getDataReady():
            self.session.open(OAWeatherDetailview, weatherhelper.favoriteList[self.currFavIdx])

    def favoriteUp(self):
        if weatherhelper.favoriteList:
            self.currFavIdx = (self.currFavIdx - 1) % len(weatherhelper.favoriteList)
            callInThread(weatherhandler.reset, weatherhelper.favoriteList[self.currFavIdx], self.configFinished)

    def favoriteDown(self):
        if weatherhelper.favoriteList:
            self.currFavIdx = (self.currFavIdx + 1) % len(weatherhelper.favoriteList)
            callInThread(weatherhandler.reset, weatherhelper.favoriteList[self.currFavIdx], self.configFinished)

    # add edit lululla
    def favoriteChoice(self):
        self.session.openWithCallback(self.returnFavoriteChoice, OAWeatherFavorites)

    def returnFavoriteChoice(self, favorite):
        if favorite is not None:
            # Mantieni tutta la logica originale di onSelect
            self.session.openWithCallback(self._finalizeFavoriteSelection, MessageBox,
                                        _("Updating weather for %s...") % favorite[0],
                                        MessageBox.TYPE_INFO, timeout=2)
            callInThread(weatherhandler.reset, favorite, self._updateAfterFavoriteChange)

    def _finalizeFavoriteSelection(self, result):
        """Callback MessageBox"""
        pass

    def _updateAfterFavoriteChange(self):
        """Callback after weather update"""
        self.startRun()
    # end edit lululla

    def config(self):
        self.session.openWithCallback(self.configFinished, WeatherSettingsView)

    def configFinished(self, result=None):
        self.clearFields()
        self.startRun()

    def error(self, errortext):
        self.clearFields()
        self["statustext"].text = errortext


class OAWeatherDetailFrame(Screen):
    def __init__(self, session):
        self.skin = weatherhelper.loadSkin("OAWeatherDetailFrame")
        Screen.__init__(self, session)
        self.widgets = ("time", "pressure", "temp", "feels", "humid", "precip", "windspeed",
                            "winddir", "windgusts", "uvindex", "visibility", "shortdesc", "longdesc")
        for widget in self.widgets:
            self[widget] = StaticText()
        self["icon"] = Pixmap()

    def showFrame(self):
        self.show()

    def updateFrame(self, dataList):
        valueMax = len(self.widgets) - 3  # except shortdesc and longdesc
        for index, widget in enumerate(self.widgets):
            value = dataList[index]
            self[widget].setText(value if value or index > valueMax else _("n/a"))
        self["icon"].instance.setPixmap(dataList[13])
        self.showFrame()

    def hideFrame(self):
        self.hide()


class OAWeatherDetailview(Screen):
    YAHOOnightswitch = {
                    "3": "47", "4": "47", "11": "45", "12": "45", "13": "46", "14": "46", "15": "46", "16": "46", "28": "27",
                    "30": "29", "32": "31", "34": "33", "37": "47", "38": "47", "40": "45", "41": "46", "42": "46", "43": "46"
                    }
    YAHOOdayswitch = {"27": "28", "29": "30", "31": "32", "33": "34", "45": "39", "46": "16", "47": "4"}

    def __init__(self, session, currlocation):
        self.skin = weatherhelper.loadSkin("OAWeatherDetailview")
        Screen.__init__(self, session)
        self.detailFrame = self.session.instantiateDialog(OAWeatherDetailFrame)
        self.detailFrameActive = False
        self.currFavIdx = weatherhelper.favoriteList.index(currlocation) if currlocation in weatherhelper.favoriteList else 0
        self.old_weatherservice = config.plugins.OAWeather.weatherservice.value
        self.detailLevels = config.plugins.OAWeather.detailLevel.getChoices()
        self.detailLevelIdx = config.plugins.OAWeather.detailLevel.getIndex()
        self.currdatehour = datetime.today().replace(minute=0, second=0, microsecond=0)
        self.currdaydelta = 0
        self.skinList = []
        self.dayList = []
        self.sunList = []
        self.moonList = []
        self.na = _("n/a")
        self.title = _("Weather Plugin Detailview")
        self["version"] = StaticText(f"OA-Weather {__version__}")
        self["detailList"] = List()
        self["update"] = Label(_("Update"))
        self["currdatetime"] = Label(self.currdatehour.strftime("%a %d %b"))
        self["sunrise"] = StaticText(self.na)
        self["sunset"] = StaticText(self.na)
        self["moonrise"] = StaticText("")
        self["moonset"] = StaticText("")
        self["moonrisepix"] = Pixmap()
        self["moonsetpix"] = Pixmap()
        self["key_red"] = StaticText(_("Exit"))
        self["key_green"] = StaticText(_("Chose favorite"))
        self["key_yellow"] = StaticText(_("Previous favorite"))
        self["key_blue"] = StaticText(_("Next favorite"))
        self["key_channel"] = StaticText(_("Day +/-"))
        self["key_info"] = StaticText(_("Details +/-"))
        self["key_ok"] = StaticText(_("Glass"))
        self["actions"] = ActionMap(["OAWeatherActions",
                                    "DirectionActions",
                                    "ColorActions",
                                    "InfoActions"], {
                                                    "ok": self.toggleDetailframe,
                                                    "cancel": self.exit,
                                                    "up": self.prevEntry,
                                                    "down": self.nextEntry,
                                                    "right": self.pageDown,
                                                    "left": self.pageUp,
                                                    "red": self.exit,
                                                    "yellow": self.favoriteUp,
                                                    "blue": self.favoriteDown,
                                                    "green": self.favoriteChoice,
                                                    "channeldown": self.prevDay,
                                                    "channelup": self.nextDay,
                                                    "info": self.toggleDetailLevel,
                                                    "menu": self.config
                                                    }, -1)
        self["statustext"] = StaticText()
        self.pressPix = self.getPixmap("barometer.png")
        self.tempPix = self.getPixmap("temp.png")
        self.feelPix = self.getPixmap("feels.png")
        self.humidPix = self.getPixmap("hygrometer.png")
        self.precipPix = self.getPixmap("umbrella.png")
        self.WindSpdPpix = self.getPixmap("wind.png")
        self.WindDirPix = self.getPixmap("compass.png")
        self.WindGustPix = self.getPixmap("windgust.png")
        self.uvIndexPix = self.getPixmap("uv_index.png")
        self.visiblePix = self.getPixmap("binoculars.png")
        self.onLayoutFinish.append(self.firstRun)

    def firstRun(self):
        moonrisepix = join(PLUGINPATH, "Images/moonrise.png")
        if exists(moonrisepix):
            self["moonrisepix"].instance.setPixmapFromFile(moonrisepix)
        self["moonrisepix"].hide()
        moonsetpix = join(PLUGINPATH, "Images/moonset.png")
        if exists(moonsetpix):
            self["moonsetpix"].instance.setPixmapFromFile(moonsetpix)
        self["detailList"].style = self.detailLevels[self.detailLevelIdx]
        self.startRun()

    def startRun(self):
        callInThread(self.parseData)

    def updateSkinList(self):
        todaydate = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        weekday = _('Today') if self.currdatehour.replace(hour=0) == todaydate else self.currdatehour.strftime("%a")
        self["currdatetime"].setText(f"{weekday} {self.currdatehour.strftime('%d %b')}")
        uvIndexPix = self.uvIndexPix if config.plugins.OAWeather.weatherservice.value != "openweather" else None  # OWM does not support UV-index at all
        iconpix = [self.pressPix, self.tempPix, self.feelPix, self.humidPix, self.precipPix, self.WindSpdPpix, self.WindDirPix, self.WindGustPix, uvIndexPix, self.visiblePix]
        if self.dayList:
            hourData = self.dayList[self.currdaydelta]
            skinList = []
            for hour in hourData:  # add set of icons to each hourly-entry
                skinList.append(tuple(hour + iconpix))
            currHour = self.currdatehour.strftime("%H:00 h")
            found, index = False, 0
            for index, hourData in enumerate(skinList):
                if currHour in hourData[0]:
                    found = True
                    break
            self["detailList"].setCurrentIndex(index if found else 0)
        else:
            hourData = ["", "", "", "", "", "", "", "", "", "", "", _("No data available."), _("No data available for this period."), None]
            skinList = [tuple(hourData + iconpix)]
        self["detailList"].updateList(skinList)
        self.skinList = skinList
        self.updateDetailFrame()

    def updateDetailFrame(self):
        if self.detailFrameActive:
            self.detailFrame.updateFrame(list(self["detailList"].getCurrent()))

    def toggleDetailframe(self):
        if self.detailFrameActive:
            self.detailFrame.hideFrame()
        self.detailFrameActive = not self.detailFrameActive
        self.updateDetailFrame()

    def toggleDetailLevel(self):
        self.detailLevelIdx ^= 1
        self["detailList"].style = self.detailLevels[self.detailLevelIdx]
        self["detailList"].updateList(self.skinList)

    def updateMoonData(self):
        if self.moonList:
            self["moonrise"].setText(datetime.fromisoformat(self.moonList[self.currdaydelta][0]).strftime("%H:%M"))
            self["moonset"].setText(datetime.fromisoformat(self.moonList[self.currdaydelta][1]).strftime("%H:%M"))
            self["moonrisepix"].show()
            self["moonsetpix"].show()
        else:
            self["moonrise"].setText("")
            self["moonset"].setText("")
            self["moonrisepix"].hide()
            self["moonsetpix"].hide()
        if self.sunList:
            self["sunrise"].setText(datetime.fromisoformat(self.sunList[self.currdaydelta][0]).strftime("%H:%M"))
            self["sunset"].setText(datetime.fromisoformat(self.sunList[self.currdaydelta][1]).strftime("%H:%M"))
        else:
            self["sunrise"].setText("")
            self["sunset"].setText("")

    def getPixmap(self, filename):
        iconfile = join(PLUGINPATH, f"Images/{filename}")
        return LoadPixmap(cached=True, path=iconfile) if exists(iconfile) else None

    def parseData(self):
        weatherservice = config.plugins.OAWeather.weatherservice.value
        if weatherservice in ["MSN", "OpenMeteo", "openweather"]:
            parser = {"MSN": self.msnparser, "OpenMeteo": self.omwparser, "openweather": self.owmparser}
            parser[weatherservice]()
            self.updateSkinList()
            self.updateMoonData()

    def msnparser(self):
        iconpath = config.plugins.OAWeather.iconset.value
        iconpath = join(ICONSETROOT, iconpath) if iconpath else join(PLUGINPATH, "Icons")
        dayList = []
        responses = weatherhandler.getFulldata().get("responses")
        if responses:  # collect latest available data
            weather = responses[0]["weather"][0]
            current = weather["current"]
            nowcasting = weather["nowcasting"]
            today = weather["forecast"]["days"][0]
            sunrisestr = today["almanac"].get("sunrise", "")
            sunrisestr = datetime.fromisoformat(sunrisestr).replace(tzinfo=None).isoformat() if sunrisestr else ""
            sunsetstr = today["almanac"].get("sunset", "")
            sunsetstr = datetime.fromisoformat(sunsetstr).replace(tzinfo=None).isoformat() if sunsetstr else ""
            created = current.get("created")
            currtime = datetime.fromisoformat(created).replace(tzinfo=None) if created else ""
            timestr = currtime.strftime("%H:%M h") if currtime else ""
            tempunit = "°C" if config.plugins.OAWeather.tempUnit.value == "Celsius" else "°F"
            press = f"{round(current.get('baro', 0))} mbar"
            temp = f"{round(current.get('temp', 0))} {tempunit}"
            feels = f"{round(current.get('feels', 0))} {tempunit}"
            humid = f"{round(current.get('rh', 0))} %"
            hourly = today["hourly"]
            precip = f"{round(hourly[0]['precip'])} %" if len(hourly) else self.na  # workaround: use value from next hour if available
            windSpd = f"{round(current.get('windSpd', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
            windDir = f"{_(weatherhandler.WI.directionsign(round(current.get('windDir', 0))))}"
            windGusts = f"{round(current.get('windGust', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
            uvIndex = f"{round(current.get('uv', 0))}"
            visibility = f"{round(current.get('vis', 0))} km"
            shortDesc = current.get("pvdrCap", "")  # e.g. 'bewölkt'
            longDesc = nowcasting.get("summary", "")  # e.g. "Der Himmel wird bewölkt."
            yahoocode = weatherhandler.WI.convert2icon("MSN", current.get("symbol", "")).get("yahooCode")  # e.g. 'n4000' -> {'yahooCode': '26', 'meteoCode': 'Y'}
            yahoocode = self.nightSwitch(yahoocode, self.getIsNight(currtime, sunrisestr, sunsetstr))
            iconfile = join(iconpath, f"{yahoocode}.png")
            iconpix = LoadPixmap(cached=True, path=iconfile) if iconfile and exists(iconfile) else None
            hourData = []
            hourData.append([timestr, press, temp, feels, humid, precip, windSpd, windDir, windGusts, uvIndex, visibility, shortDesc, longDesc, iconpix])
            days = weather["forecast"]["days"]
            if days:
                self.sunList = []
                self.moonList = []
                for index, day in enumerate(days):  # collect data on future hours of current day
                    if index:
                        hourData = []
                    almanac = day.get("almanac", {})
                    sunrisestr = almanac.get("sunrise", "")
                    sunrisestr = datetime.fromisoformat(sunrisestr).replace(tzinfo=None).isoformat() if sunrisestr else ""
                    sunsetstr = almanac.get("sunset", "")
                    sunsetstr = datetime.fromisoformat(sunsetstr).replace(tzinfo=None).isoformat() if sunsetstr else ""
                    moonrisestr = almanac.get("moonrise", "")
                    moonrisestr = datetime.fromisoformat(moonrisestr).replace(tzinfo=None).isoformat() if moonrisestr else ""
                    moonsetstr = almanac.get("moonset", "")
                    moonsetstr = datetime.fromisoformat(moonsetstr).replace(tzinfo=None).isoformat() if moonsetstr else ""
                    for hour in day.get("hourly", []):
                        valid = hour.get("valid")
                        currtime = datetime.fromisoformat(valid).replace(tzinfo=None) if valid else ""
                        timestr = currtime.strftime("%H:%M h") if currtime else ""
                        press = f"{round(hour.get('baro', 0))} mbar"
                        tempunit = "°C" if config.plugins.OAWeather.tempUnit.value == "Celsius" else "°F"
                        temp = f"{round(hour.get('temp', 0))} {tempunit}"
                        feels = f"{round(hour.get('feels', 0))} {tempunit}"
                        humid = f"{round(hour.get('rh', 0))} %"
                        precip = f"{round(hour.get('precip', 0))} %"
                        windSpd = f"{round(hour.get('windSpd', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
                        windDir = f"{_(weatherhandler.WI.directionsign(round(hour.get('windDir', 0))))}"
                        windGusts = f"{round(hour.get('windGust', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
                        uvIndex = f"{round(hour.get('uv', 0))}"
                        visibility = f"{round(hour.get('vis', 0))} km"
                        shortDesc = hour.get("pvdrCap", "")  # e.g. 'bewölkt'
                        longDesc = hour.get("summary", "")  # e.g. "Der Himmel wird bewölkt."
                        yahoocode = weatherhandler.WI.convert2icon("MSN", hour.get("symbol", "")).get("yahooCode")  # e.g. 'n4000' -> {'yahooCode': '26', 'meteoCode': 'Y'}
                        yahoocode = self.nightSwitch(yahoocode, self.getIsNight(currtime, sunrisestr, sunsetstr))
                        iconfile = join(iconpath, f"{yahoocode}.png")
                        iconpix = LoadPixmap(cached=True, path=iconfile) if iconfile and exists(iconfile) else None
                        hourData.append([timestr, press, temp, feels, humid, precip, windSpd, windDir, windGusts, uvIndex, visibility, shortDesc, longDesc, iconpix])
                    dayList.append(hourData)
                    self.sunList.append((sunrisestr, sunsetstr))
                    self.moonList.append((moonrisestr, moonsetstr))
        self.dayList = dayList

    def omwparser(self):
        iconpath = config.plugins.OAWeather.iconset.value
        iconpath = join(ICONSETROOT, iconpath) if iconpath else join(PLUGINPATH, "Icons")
        fulldata = weatherhandler.getFulldata()
        if fulldata:
            daily = fulldata.get("daily", {})
            sunriseList = daily.get("sunrise", [])
            sunsetList = daily.get("sunset", [])
            self.sunList = []
            for index, sunrisestr in enumerate(sunriseList):
                sunsetstr = sunsetList[index]
                self.sunList.append((sunrisestr if sunrisestr else self.na, sunsetstr if sunsetstr else self.na))
            self.moonList = []  # OMW does not support moonrise / moonset at all
            hourly = fulldata.get("hourly", {})
            dayList = []
            if hourly:
                timeList = hourly.get("time", [])
                pressList = hourly.get("pressure_msl")
                tempList = hourly.get("temperature_2m", [])
                feelsList = hourly.get("apparent_temperature", [])
                humidList = hourly.get("relativehumidity_2m", [])
                precipList = hourly.get("precipitation_probability", [])
                wSpeedList = hourly.get("windspeed_10m", [])
                wGustList = hourly.get("wind_gusts_10m", [])
                wDirList = hourly.get("winddirection_10m", [])
                uvList = hourly.get("uv_index", [])
                visList = hourly.get("visibility", [])
                wCodeList = hourly.get("weathercode", [])
                currday = datetime.fromisoformat(timeList[0]).replace(hour=0, minute=0, second=0, microsecond=0)
                daycount = 0
                hourData = []
                for idx, isotime in enumerate(timeList):
                    currtime = datetime.fromisoformat(isotime)
                    timestr = currtime.strftime("%H:%M h")
                    press = f"{round(pressList[idx])} mbar"
                    tempunit = "°C" if config.plugins.OAWeather.tempUnit.value == "Celsius" else "°F"
                    temp = f"{round(tempList[idx])} {tempunit}"
                    feels = f"{round(feelsList[idx])} {tempunit}"
                    humid = f"{round(humidList[idx])} %"
                    precip = f"{round(precipList[idx])} %"
                    windSpd = f"{round(wSpeedList[idx])} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
                    windDir = f"{_(weatherhandler.WI.directionsign(round(round(wDirList[idx]))))}"
                    windGusts = f"{round(wGustList[idx])} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
                    uvIndex = f"{round(uvList[idx])}"
                    visibility = f"{round(visList[idx] / 1000)} km"
                    shortDesc, longDesc = "", ""  # OMW does not support description texts at all
                    isNight = self.getIsNight(currtime, sunriseList[daycount], sunsetList[daycount])
                    yahoocode = self.nightSwitch(weatherhandler.WI.convert2icon("OMW", wCodeList[idx]).get("yahooCode"), isNight)  # e.g. '1' -> {'yahooCode': '34', 'meteoCode': 'B'}
                    iconfile = join(iconpath, f"{yahoocode}.png")
                    iconpix = LoadPixmap(cached=True, path=iconfile) if iconfile and exists(iconfile) else None
                    hourData.append([timestr, press, temp, feels, humid, precip, windSpd, windDir, windGusts, uvIndex, visibility, shortDesc, longDesc, iconpix])
                    timeday = currtime.replace(hour=0, minute=0, second=0, microsecond=0)
                    if timeday > currday:  # is a new day?
                        currday = timeday
                        daycount += 1
                        dayList.append(hourData)
                        hourData = []
            self.dayList = dayList

    def owmparser(self):
        iconpath = config.plugins.OAWeather.iconset.value
        iconpath = join(ICONSETROOT, iconpath) if iconpath else join(PLUGINPATH, "Icons")
        fulldata = weatherhandler.getFulldata()
        if fulldata:
            city = fulldata.get("city", {})
            sunriseTs, sunsetTs = city.get("sunrise", 0), city.get("sunset", 0)  # OM only supports sunris/sunset of today
            sunrisestr = datetime.fromtimestamp(sunriseTs).isoformat() if sunriseTs else ""
            sunsetstr = datetime.fromtimestamp(sunsetTs).isoformat() if sunsetTs else ""
            self.sunList, self.moonList = [], []  # OMW does not support moonrise / moonset at all
            hourData = []
            tempunit = "°C" if config.plugins.OAWeather.tempUnit.value == "Celsius" else "°F"
            timeTs = fulldata.get("dt", 0)  # collect latest available data
            timestr = datetime.fromtimestamp(timeTs).strftime("%H:%M") if timeTs else ""
            main = fulldata.get("main", {})
            hourly = fulldata.get("list", {})
            press = f"{round(main.get('pressure', 0))} mbar"
            temp = f"{round(main.get('temp', 0))} {tempunit}"
            feels = f"{round(main.get('feels_like', 0))} {tempunit}"
            humid = f"{round(main.get('humidity', 0))} %"
            precip = f"{round(hourly[0].get('pop', 0) * 100)} %"
            wind = fulldata.get('wind', {})
            windSpd = f"{round(wind.get('speed', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
            windDir = f"{_(weatherhandler.WI.directionsign(round(wind.get('deg', 0))))}"
            windGusts = f"{round(hourly[0].get('wind', {}).get('gust', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
            uvIndex = ""  # OWM does not support UV-index at all
            visibility = f"{round(fulldata.get('visibility', 0) / 1000)} km"
            weather = fulldata.get("weather", [""])[0]
            shortDesc = weather.get("description", "")
            longDesc = ""  # OWM does not support long descriptions at all
            currtime = datetime.fromtimestamp(timeTs)
            isNight = self.getIsNight(currtime, sunrisestr, sunsetstr)
            yahoocode = self.nightSwitch(weatherhandler.WI.convert2icon("OWM", weather.get("id", "n/a")).get("yahooCode"), isNight)  # e.g. '801' -> {'yahooCode': '34', 'meteoCode': 'B'}
            iconfile = join(iconpath, f"{yahoocode}.png")
            iconpix = LoadPixmap(cached=True, path=iconfile) if iconfile and exists(iconfile) else None
            hourData.append([timestr, press, temp, feels, humid, precip, windSpd, windDir, windGusts, uvIndex, visibility, shortDesc, longDesc, iconpix])
            dayList = []
            if hourly:
                currday = datetime.fromisoformat(hourly[0].get("dt_txt", "1900-01-01 00:00:00")).replace(hour=0, minute=0, second=0, microsecond=0)
                for hour in hourly:  # collect data on future hours of current day
                    isotime = hour.get("dt_txt", "1900-01-01 00:00:00")
                    timestr = isotime[11:16]
                    main = hour.get("main", {})
                    press = f"{round(main.get('pressure', 0))} mbar"
                    temp = f"{round(main.get('temp', 0))} {tempunit}"
                    feels = f"{round(main.get('feels_like', 0))} {tempunit}"
                    humid = f"{round(main.get('humidity', 0))} %"
                    precip = f"{round(hour.get('pop', 0) * 100)} %"
                    wind = hour.get("wind", {})
                    windSpd = f"{round(wind.get('speed', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
                    windDir = f"{_(weatherhandler.WI.directionsign(round(wind.get('deg', 0))))}"
                    windGusts = f"{round(wind.get('gust', 0))} {'km/h' if config.plugins.OAWeather.windspeedMetricUnit.value == 'km/h' else 'm/s'}"
                    uvIndex = ""  # OWM does not support UV-index at all
                    visibility = f"{round(hour.get('visibility', 0) / 1000)} km"
                    weather = hour.get("weather", [""])[0]
                    shortDesc = weather.get("description", "")
                    longDesc = ""  # OWM does not support long descriptions at all
                    currtime = datetime.fromisoformat(isotime)
                    isNight = self.getIsNight(currtime, sunrisestr, sunsetstr)
                    yahoocode = self.nightSwitch(weatherhandler.WI.convert2icon("OWM", weather.get("id", "n/a")).get("yahooCode"), isNight)  # e.g. '801' -> {'yahooCode': '34', 'meteoCode': 'B'}
                    iconfile = join(iconpath, f"{yahoocode}.png")
                    iconpix = LoadPixmap(cached=True, path=iconfile) if iconfile and exists(iconfile) else None
                    hourData.append([timestr, press, temp, feels, humid, precip, windSpd, windDir, windGusts, uvIndex, visibility, shortDesc, longDesc, iconpix])
                    timeday = currtime.replace(hour=0, minute=0, second=0, microsecond=0)
                    if timeday > currday:  # is a new day?
                        currday = timeday
                        dayList.append(hourData)
                        hourData = []
                        self.sunList.append((sunrisestr, sunsetstr))
            self.dayList = dayList

    def getIsNight(self, currtime, sunrisestr, sunsetstr):
        if sunrisestr and sunsetstr:
            sunrise = datetime.fromisoformat(sunrisestr)
            sunset = datetime.fromisoformat(sunsetstr)
            isNight = True if currtime < sunrise or currtime > sunset else False
        else:
            isNight = False
        return isNight

    def nightSwitch(self, iconcode, isNight):
        return self.YAHOOnightswitch.get(iconcode, iconcode) if config.plugins.OAWeather.nighticons.value and isNight else self.YAHOOdayswitch.get(iconcode, iconcode)

    def favoriteUp(self):
        if weatherhelper.favoriteList:
            self.currFavIdx = (self.currFavIdx - 1) % len(weatherhelper.favoriteList)
            callInThread(weatherhandler.reset, weatherhelper.favoriteList[self.currFavIdx], callback=self.parseData)

    def favoriteDown(self):
        if weatherhelper.favoriteList:
            self.currFavIdx = (self.currFavIdx + 1) % len(weatherhelper.favoriteList)
            callInThread(weatherhandler.reset, weatherhelper.favoriteList[self.currFavIdx], callback=self.parseData)

    def favoriteChoice(self):
        choiceList = [(item[0], item) for item in weatherhelper.favoriteList]
        self.session.openWithCallback(self.returnFavoriteChoice, ChoiceBox, titlebartext=_("Select desired location"), title="", list=choiceList)

    def returnFavoriteChoice(self, favorite):
        if favorite is not None:
            callInThread(weatherhandler.reset, favorite[1], callback=self.parseData)

    def prevEntry(self):
        self["detailList"].up()
        self.updateDetailFrame()

    def nextEntry(self):
        self["detailList"].down()
        self.updateDetailFrame()

    def pageDown(self):
        self["detailList"].pageDown()
        self.updateDetailFrame()

    def pageUp(self):
        self["detailList"].pageUp()
        self.updateDetailFrame()

    def prevDay(self):
        self.currdaydelta = (self.currdaydelta - 1) % len(self.dayList)
        self.currdatehour = datetime.today().replace(minute=0, second=0, microsecond=0) + timedelta(days=self.currdaydelta)
        callInThread(weatherhandler.reset, callback=self.parseData)

    def nextDay(self):
        self.currdaydelta = (self.currdaydelta + 1) % len(self.dayList)
        self.currdatehour = datetime.today().replace(minute=0, second=0, microsecond=0) + timedelta(days=self.currdaydelta)
        callInThread(weatherhandler.reset, callback=self.parseData)

    def config(self):
        self.old_weatherservice = config.plugins.OAWeather.weatherservice.value
        if self.detailFrameActive:
            self.detailFrame.hideFrame()
        self.session.openWithCallback(self.configFinished, WeatherSettingsView)

    def configFinished(self, result=None):
        self.detailLevelIdx = config.plugins.OAWeather.detailLevel.getIndex()
        if self.detailFrameActive:
            self.detailFrame.showFrame()
        if self.old_weatherservice != config.plugins.OAWeather.weatherservice.value:
            callInThread(weatherhandler.reset, callback=self.parseData)
        else:
            self.startRun()

    def exit(self):
        if self.detailFrameActive:
            self.detailFrame.hide()
            self.detailFrameActive = False
        else:
            self.session.deleteDialog(self.detailFrame)
            self.close()


# class fixed from lululla for management favorites
class OAWeatherFavorites(Screen):
    def __init__(self, session):
        self.skin = weatherhelper.loadSkin("OAWeatherFavorites")
        Screen.__init__(self, session)

        self.favoritefile = resolveFilename(SCOPE_CONFIG, "oaweather_fav.dat")  # Manteniamo .dat
        self.newFavList = weatherhelper.favoriteList[:]
        self.selected_index = None
        self.pending_changes = False

        self["favoriteList"] = List(enableWrapAround=True)
        self["headline"] = StaticText(_("Manage Favorites"))
        self["key_red"] = StaticText(_("Delete"))
        self["key_green"] = StaticText(_("Save"))
        self["key_yellow"] = StaticText(_("Edit"))
        self["key_blue"] = StaticText(_("Add"))

        self["actions"] = ActionMap(
            ["OAWeatherFavoritesActions", "ColorActions", "OkCancelActions"],
            {
                "ok": self.onSelect,
                "cancel": self.onCancel,
                "red": self.onDelete,
                "green": self.onSave,
                "yellow": self.onEdit,
                "blue": self.startAddFavorite,
                "up": self.onUp,
                "down": self.onDown
            },
            -1
        )
        self.onShown.append(self.initScreen)

    def initScreen(self):
        """Initialize when screen becomes visible"""
        self._refreshList()
        self.checkCurrentLocation()

    def _refreshList(self):
        """Update the list of favorites"""
        try:
            list_items = [
                (fav[0], f"[lon={fav[1]}, lat={fav[2]}]", idx)
                for idx, fav in enumerate(self.newFavList)
            ]
            self["favoriteList"].setList(list_items)
        except Exception as e:
            print(f"[OAWeather] Error updating list: {str(e)}")
            self.session.open(MessageBox, _("Error updating list"), MessageBox.TYPE_ERROR, timeout=3)

    def checkCurrentLocation(self):
        """Highlight current location if present"""
        current = config.plugins.OAWeather.weatherlocation.value
        if current in self.newFavList:
            idx = self.newFavList.index(current)
            self["favoriteList"].setIndex(idx)

    def startAddFavorite(self):
        """Start adding a new favorite location"""
        self.session.openWithCallback(
            self.cityNameEntered,
            VirtualKeyBoard,
            title=_("Enter city name (e.g. 'Rome, IT')"),
            text=""
        )

    def cityNameEntered(self, city_name):
        """Handle the city name entered in VirtualKeyBoard"""
        if city_name:
            self._startCitySearch(city_name)

    def _startCitySearch(self, city_name):
        """Start city search after name is entered"""
        if city_name and len(city_name) >= 3:
            callInThread(self._performCitySearch, city_name)
        else:
            self.session.open(MessageBox, _("Please enter at least 3 characters"), MessageBox.TYPE_WARNING, timeout=3)

    def _performCitySearch(self, city_name):
        """Perform the actual city search in a thread"""
        try:
            services = {"MSN": "msn", "OpenMeteo": "omw", "openweather": "owm"}
            service = services.get(config.plugins.OAWeather.weatherservice.value, "msn")
            apikey = config.plugins.OAWeather.apikey.value
            WI = Weatherinfo(service, apikey)

            if WI.error:
                self.session.open(MessageBox, text=WI.error, type=MessageBox.TYPE_ERROR)
                return

            geodataList = WI.getCitylist(city_name, config.osd.language.value.replace('_', '-').lower(), count=15)

            if WI.error or geodataList is None or len(geodataList) == 0:
                self.session.open(MessageBox, text=_("City '%s' not found! Please try another wording." % city_name), type=MessageBox.TYPE_WARNING)
            else:
                cityList = []
                for item in geodataList:
                    try:
                        cityList.append((item[0], item[1], item[2]))
                    except Exception:
                        print("[OAWeather] Error in city search result")

                # Convert to the format expected by ChoiceBox
                choiceList = [(f"{item[0]} [lon={item[1]}, lat={item[2]}]", item) for item in cityList]
                self.session.openWithCallback(self._handleSearchResult, ChoiceBox, title=_("Select your location"), list=choiceList)

        except Exception as e:
            print(f"[OAWeather] Error in city search: {str(e)}")
            self.session.open(MessageBox, text=_("Error searching for location"), type=MessageBox.TYPE_ERROR)

    def _handleSearchResult(self, result):
        """Handle the selected search result"""
        if result is not None:
            weathercity, lon, lat = result[1]
            location = (weatherhelper.reduceCityname(weathercity), lon, lat)
            self._addToFavorites(location)

    def _addToFavorites(self, location):
        """Add location to favorites"""
        # Check for duplicates
        for existing in self.newFavList:
            if existing[0].lower() == location[0].lower():
                self.session.open(MessageBox, _("Location already exists"), MessageBox.TYPE_INFO, timeout=3)
                return
            if abs(existing[1] - location[1]) < 0.01 and abs(existing[2] - location[2]) < 0.01:
                self.session.open(MessageBox, _("Location with similar coordinates already exists"), MessageBox.TYPE_INFO, timeout=3)
                return

        self.newFavList.append(location)
        self._refreshList()
        self.pending_changes = True
        self.session.open(MessageBox, _("Location added successfully"), MessageBox.TYPE_INFO, timeout=2)

    def onSelect(self):
        """Versione originale funzionante al 100% - NON MODIFICARE"""
        try:
            selected = self["favoriteList"].getCurrent()
            if not selected:
                return

            print(f"Selected item RAW: {selected}")

            # Get the original data from newFavList using the index
            if isinstance(selected, (tuple, list)) and len(selected) >= 3:
                location_data = self.newFavList[selected[2]]
            else:
                # Fallback if format is different
                location_data = selected

            print(f"Location data to save: {location_data}")

            # Update all relevant config values
            config.plugins.OAWeather.weathercity.value = location_data[0]
            config.plugins.OAWeather.owm_geocode.value = f"{location_data[1]},{location_data[2]}"
            config.plugins.OAWeather.weatherlocation.value = (location_data[0], location_data[1], location_data[2])

            # Save config immediately
            config.plugins.OAWeather.save()
            configfile.save()

            # Update weatherhelper favorites if needed
            if location_data not in weatherhelper.favoriteList:
                weatherhelper.addFavorite(location_data)

            print(f"Config updated to: {location_data[0]}")

            # Reset weather data with new location
            callInThread(weatherhandler.reset, location_data)

            # Close and return selected location
            self.close(location_data)

        except Exception as e:
            print(f"Selection failed: {str(e)}")
            self.session.open(MessageBox, _("Error selecting location"), MessageBox.TYPE_ERROR, timeout=3)

    def onCancel(self):
        if self.pending_changes:
            self.session.openWithCallback(
                self._handleExitConfirmation,
                MessageBox,
                _("You have unsaved changes. Save before exiting?"),
                MessageBox.TYPE_YESNO
            )
        else:
            self.close(None)

    def _handleExitConfirmation(self, result):
        if result is None:
            return
        elif result:
            self.onSave()
        else:
            self.close(None)

    def onDelete(self):
        """Delete selected favorite"""
        current = self.getCurrentFavorite()
        if current:
            self.session.openWithCallback(
                lambda result: self.confirmDelete(current, result),
                MessageBox,
                _("Delete {}?").format(current[0]),
                MessageBox.TYPE_YESNO
            )

    def confirmDelete(self, favorite, confirmed):
        """Delete location with full synchronization"""
        if confirmed:
            try:
                # 1. Remove from both lists
                if favorite in self.newFavList:
                    self.newFavList.remove(favorite)
                if favorite in weatherhelper.favoriteList:
                    weatherhelper.favoriteList.remove(favorite)

                # 2. Atomic save
                weatherhelper.saveFavorites()  # Uses helper's method

                # 3. Clear cache
                if exists(CACHEFILE):
                    remove(CACHEFILE)

                # 4. Check if deleted was active location
                current_loc = config.plugins.OAWeather.weatherlocation.value
                if current_loc == favorite:
                    config.plugins.OAWeather.weatherlocation.value = weatherhelper.locationDefault
                    config.plugins.OAWeather.weathercity.value = weatherhelper.locationDefault[0]
                    config.plugins.OAWeather.owm_geocode.value = f"{weatherhelper.locationDefault[1]},{weatherhelper.locationDefault[2]}"
                    config.plugins.OAWeather.save()
                    configfile.save()
                    weatherhandler.reset(weatherhelper.locationDefault)

                # 5. Sync all configs
                weatherhelper.syncWithConfig()

                # 6. Update UI
                self._refreshList()
                self.session.open(MessageBox, _("Location deleted"), MessageBox.TYPE_INFO, timeout=3)

            except Exception as e:
                print(f"Delete error: {str(e)}")
                self.session.open(MessageBox, _("Delete failed"), MessageBox.TYPE_ERROR, timeout=3)

    def onSave(self):
        """Salva i preferiti usando il metodo di WeatherHelper"""
        try:
            weatherhelper.setFavoriteList(self.newFavList)
            weatherhelper.saveFavorites()  # Questo userà pickle e .dat

            # Aggiorna le scelte nella configurazione
            config.plugins.OAWeather.weatherlocation.setChoices([(item, item[0]) for item in self.newFavList])

            self.session.open(MessageBox, _("Favorites saved!"), MessageBox.TYPE_INFO, timeout=2)
        except Exception as e:
            print(f"[OAWeather] Save error: {str(e)}")
            self.session.open(MessageBox, _("Error saving favorites"), MessageBox.TYPE_ERROR, timeout=3)

    def onEdit(self):
        """Edit selected favorite"""
        current = self.getCurrentFavorite()
        if current:
            self.selected_index = self["favoriteList"].getIndex()
            self.session.openWithCallback(
                self.handleEditResult,
                VirtualKeyBoard,
                title=_("Edit city name"),
                text=current[0]
            )

    def handleEditResult(self, new_name):
        """Handle edit result"""
        if new_name and self.selected_index is not None:
            try:
                old = self.newFavList[self.selected_index]
                self.newFavList[self.selected_index] = (new_name, old[1], old[2])
                self.pending_changes = True
                self._refreshList()
            except IndexError:
                self.session.open(MessageBox, _("Invalid selection"), MessageBox.TYPE_ERROR, timeout=3)

    def getCurrentFavorite(self):
        """Get currently selected favorite"""
        idx = self["favoriteList"].getIndex()
        if 0 <= idx < len(self.newFavList):
            return self.newFavList[idx]
        return None

    def onUp(self):
        """Handle up action"""
        self["favoriteList"].up()

    def onDown(self):
        """Handle down action"""
        self["favoriteList"].down()


weatherhandler = WeatherHandler()
