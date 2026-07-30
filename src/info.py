import os
import logging
import gi
from i18n import _, setup_i18n

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw, Gtk, Gdk
from config import Config

logger = logging.getLogger("Shellix")

class Info:
    def __init__(self, parent):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_icon_dir = os.path.join(base_dir, 'data', 'icons')

        display = Gdk.Display.get_default()
        if display:
            icon_theme = Gtk.IconTheme.get_for_display(display)
            if os.path.exists(local_icon_dir):
                try:
                    search_path = icon_theme.get_search_path()
                    if local_icon_dir not in search_path:
                        icon_theme.add_search_path(local_icon_dir)
                except Exception as e:
                    logger.warning(f"Failed to update icon path: {e}")

        self.about = Adw.AboutWindow(
            transient_for=parent,
            application_name=Config.APP_NAME,
            application_icon=Config.APP_ID,
            version=Config.CURRENT_VERSION,
            comments=_('Виртуальный терминал для Linux с поддержкой вкладок и настраиваемыми параметрами'),
            developers=['Egor Kurochkin'],
            copyright='© 2026 Egor Kurochkin\nhttps://github.com/itsegork/shellix',
            license_type=Gtk.License.MIT_X11,
            issue_url=f'https://github.com/{Config.GITHUB_REPO}/issues',
            website=f'https://github.com/{Config.GITHUB_REPO}'
        )

        self.about.add_credit_section('Material Icons', ['Google LLC'])
        self.about.add_credit_section(
            'PyGObject, GTK4, LibAdwaita, GLib, Gio, GObject, Gdk, Pango, VTE, nautilus-python',
            ['The GNOME Project']
        )
        self.about.add_credit_section('requests', ['Kenneth Reitz'])
        self.about.add_credit_section('psutil', ['Giampaolo Rodola', 'Jay Loden', 'Dave Daeschler'])
        self.about.add_credit_section('conspy', ['Russell Stuart'])

        self.about.add_legal_section('Material Icons', '© 2026 Google LLC\nhttps://fonts.google.com/icons', Gtk.License.APACHE_2_0, None)
        self.about.add_legal_section('requests', '© 2026 Kenneth Reitz\nhttps://github.com/psf/requests', Gtk.License.APACHE_2_0, None)
        self.about.add_legal_section('PyGObject, GTK4, LibAdwaita, GLib, Gio, GObject, Gdk, Pango, VTE, nautilus-python', '© 2026 The GNOME Project.\nhttps://gitlab.gnome.org/', Gtk.License.LGPL_2_1, None)
        self.about.add_legal_section('psutil', '© 2026 Giampaolo Rodola, Dave Daeschler, Jay Loden\nhttps://github.com/giampaolo/psutil', Gtk.License.BSD_3, None)
        self.about.add_legal_section('conspy', '© 2026 Russell Stuart\nhttps://sourceforge.net/p/conspy/code/ci/default/tree/', Gtk.License.AGPL_3_0, None)

        self.about.present()