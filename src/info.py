import gi
import os
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw, Gtk, Gdk
from config import Config

class Info:
    def __init__(self, parent):
        icon_path = os.path.join('data', 'icons', 'ru.itsegork.shellix.svg')
        icon_id = 'ru.itsegork.shellix'
        display = Gdk.Display.get_default()
        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_dir = os.path.dirname(icon_path)
        if os.path.exists(icon_dir):
            icon_theme.add_search_path(icon_dir)

        about = Adw.AboutWindow(transient_for=parent, 
        application_name=Config.APP_NAME, 
        application_icon=icon_id, 
        version=Config.CURRENT_VERSION, 
        comments='Виртуальный терминал для Linux с поддержкой вкладок и настраиваемыми параметрами', 
        developers=['Egor Kurochkin'], 
        copyright='© 2026 Egor Kurochkin\nhttps://github.com/itsegork/shellix', 
        license_type=Gtk.License.MIT_X11, 
        website=f'https://github.com/{Config.GITHUB_REPO}')

        about.add_credit_section('Material Icons', ['Google LLC'])
        about.add_credit_section('PyGObject, GTK4, LibAdwaita, GLib, Gio, GObject, Gdk, Pango', ['The GNOME Project'])
        about.add_credit_section('requests', ['Kenneth Reitz'])
        about.add_credit_section('psutil', ['Giampaolo Rodola', 'Jay Loden', 'Dave Daeschler'])
        about.add_credit_section('conspy', ['Russell Stuart'])

        about.add_legal_section('Material Icons', '© 2026 Google LLC\nhttps://fonts.google.com/icons', Gtk.License.APACHE_2_0, None)
        about.add_legal_section('requests', '© 2026 Kenneth Reitz\nhttps://github.com/psf/requests', Gtk.License.APACHE_2_0, None)
        about.add_legal_section('PyGObject, GTK4, LibAdwaita, GLib, Gio, GObject, Gdk, Pango, VTE', '© 2026 The GNOME Project.\nhttps://gitlab.gnome.org/', Gtk.License.LGPL_2_1, None)
        about.add_legal_section('psutil', '© 2026  Giampaolo Rodola, Dave Daeschler, Jay Loden\nhttps://github.com/giampaolo/psutil', Gtk.License.BSD_3, None)
        about.add_legal_section('conspy', '© 2020 Russell Stuart\nhttps://sourceforge.net/p/conspy/code/ci/default/tree/', Gtk.License.AGPL_3_0, None)

        about.present()