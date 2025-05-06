from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

__version__ = "2.1"

PluginLanguageDomain = "OAWeather"
PluginLanguagePath = "Extensions/OAWeather/locale"


def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	t = gettext.dgettext(PluginLanguageDomain, txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t


localeInit()
language.addCallback(localeInit)
