import os
import gettext
import locale

DOMAIN = "shellix"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE_DIR = os.path.join(BASE_DIR, "locale")

_ = gettext.gettext
def setup_i18n():
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass

    gettext.bindtextdomain(DOMAIN, LOCALE_DIR)
    gettext.textdomain(DOMAIN)

    import builtins
    builtins._ = gettext.gettext

