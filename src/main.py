import gi
import sys
import os
import time
import ctypes
import ctypes.util
import logging
from urllib.parse import unquote
from i18n import _, setup_i18n
setup_i18n()

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import Adw, Gtk, Gio, Gdk, GLib
import psutil

from config import Config
from terminal import ShellixTerminal
from preferences import PreferencesWindow
from info import Info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Shellix")

def set_process_name(name: str):
    try:
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        buff = ctypes.create_string_buffer(name.encode('utf-8'), 16)
        libc.prctl(15, ctypes.byref(buff), 0, 0, 0)
    except Exception as e:
        logger.debug(f"Failed to set process name: {e}")


class TTYDialog(Adw.Window):
    def __init__(self, parent, callback):
        super().__init__(transient_for=parent, modal=True)
        self.set_title(_("Подключение к TTY"))
        self.set_default_size(420, -1)
        self.set_resizable(False)
        self.callback = callback

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()
        header.set_show_title(True)
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label=_("Отмена"))
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        connect_btn = Gtk.Button(label=_("Подключиться"))
        connect_btn.add_css_class("suggested-action")
        connect_btn.connect("clicked", self.on_connect_clicked)
        header.pack_end(connect_btn)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(380)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        toolbar_view.set_content(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(box)

        group_tty = Adw.PreferencesGroup(
            title=_("Параметры сессии"),
            description=_("Доступны виртуальные консоли TTY 3, 4, 5 и 6")
        )
        box.append(group_tty)

        row_num = Adw.ActionRow(
            title=_("Номер TTY"),
            subtitle=_("Укажите номер консоли")
        )
        group_tty.add(row_num)

        self.entry_num = Gtk.SpinButton.new_with_range(3, 6, 1)
        self.entry_num.set_value(3)
        self.entry_num.set_valign(Gtk.Align.CENTER)
        row_num.add_suffix(self.entry_num)

        group_info = Adw.PreferencesGroup(
            title=_("Информация и предупреждения")
        )
        box.append(group_info)

        self.info_row = Adw.ActionRow(
            title=_("Conspy"),
            subtitle=_("Возможны проблемы с геометрией и вылеты на мониторах с высоким разрешением.")
        )
        group_info.add(self.info_row)

    def on_connect_clicked(self, btn):
        tty_num = int(self.entry_num.get_value())
        self.callback(tty_num)
        self.close()


class ShellixWindow(Adw.ApplicationWindow):
    def __init__(self, app, settings, initial_path=None):
        super().__init__(application=app)
        
        self.settings = settings
        self.initial_path = initial_path
        self.set_title(Config.APP_NAME)
        
        self.set_default_size(
            self.settings.get("window_width", 800), 
            self.settings.get("window_height", 600)
        )
        
        if self.settings.get("is_maximized"):
            self.maximize()
            
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        
        self._stats_timer_id = None
        
        self.setup_ui()
        self.setup_actions()
        
        Config.watch(self.on_settings_reloaded)
        self.new_tab(path=self.initial_path)
        
        self.connect("close-request", self.on_close_request)
        
        self._stats_timer_id = GLib.timeout_add_seconds(2, self.update_system_stats)

    def setup_ui(self):
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)
        self.add_toast = self.toast_overlay.add_toast

        self.header = Adw.HeaderBar()
        self.stats_label = Gtk.Label(label=_("Загрузка..."))
        self.stats_label.add_css_class("title")
        self.header.set_title_widget(self.stats_label)
        
        menu = Gio.Menu.new()
        menu.append(_("Новое окно"), "app.new_window")
        menu.append(_("Настройки"), "win.preferences")
        menu.append(_("Подключиться к TTY"), "win.connect_tty")
        menu.append(_("О программе"), "win.about")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        self.header.pack_end(menu_button)
        main_box.append(self.header)

        self.tab_view = Adw.TabView()
        self.tab_view.connect("close-page", self.on_page_close_request)
        self.tab_view.connect("setup-menu", self.on_setup_tab_menu)
        self.tab_view.connect("notify::selected-page", self.on_tab_changed)

        self.tab_bar = Adw.TabBar(view=self.tab_view)
        self.tab_bar.set_autohide(False)
        self.tab_bar.set_expand_tabs(True)
        
        new_tab_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        new_tab_btn.add_css_class("flat")
        new_tab_btn.set_action_name("win.new_tab")
        self.tab_bar.set_end_action_widget(new_tab_btn)

        main_box.append(self.tab_bar)
        main_box.append(self.tab_view)
        self.apply_clean_styles()

    def setup_actions(self):
        actions = {
            "new_tab": lambda *args: self.new_tab(),
            "close_tab": lambda *args: self.close_current_tab(),
            "preferences": lambda *args: self.show_preferences(),
            "about": lambda *args: Info(self),
            "connect_tty": lambda *args: self.show_tty_dialog(),
            "copy": lambda *args: self.do_copy(),
            "paste": lambda *args: self.do_paste()
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def update_system_stats(self) -> bool:
        show_cpu = self.settings.get("show_cpu", True)
        show_ram = self.settings.get("show_ram", True)
        show_disk = self.settings.get("show_disk", True)
        show_net = self.settings.get("show_net", True)

        if not any([show_cpu, show_ram, show_disk, show_net]):
            self.stats_label.set_visible(False)
            return True

        self.stats_label.set_visible(True)

        try:
            parts = []
            if show_cpu:
                cpu = psutil.cpu_percent()
                parts.append(f"  {cpu}%")
            if show_ram:
                vm = psutil.virtual_memory()
                parts.append(f"󰘚  {vm.used/(1024**3):.1f}/{vm.total/(1024**3):.1f} GB")
            if show_disk:
                du = psutil.disk_usage('/')
                parts.append(f"󰋊  {du.used/(1024**3):.0f}/{du.total/(1024**3):.0f} GB")
            if show_net:
                net_io = psutil.net_io_counters()
                now = time.time()
                elapsed = max(now - self.last_time, 0.1)
                dl = (net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed / 1024
                ul = (net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed / 1024
                self.last_net_io = net_io
                self.last_time = now
                parts.append(f"󰓅  {dl:.1f}↓ {ul:.1f}↑ {_('КБ/с')}")

            stats = "  ".join(parts) if parts else Config.APP_NAME
            self.stats_label.set_label(stats)
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            self.stats_label.set_label(Config.APP_NAME)

        return True

    def apply_clean_styles(self):
        provider = Gtk.CssProvider()
        css = """
            headerbar { border-bottom: none; box-shadow: none; }
            headerbar label.title { font-feature-settings: "tnum"; }
            tabbar { border: none; background-color: @window_bg_color; }
            scrolledwindow, tabview { border: none; background-color: transparent; }
        """
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), 
            provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def new_tab(self, path=None):
        terminal = ShellixTerminal(self.settings, is_tty=False, work_dir=path)
        terminal.connect("child-exited", lambda t, s: self.on_terminal_child_exited(t))

        scrolled = Gtk.ScrolledWindow(child=terminal)
        page = self.tab_view.append(scrolled)
        page.set_title("Terminal")

        terminal.connect(
            "window-title-changed", 
            lambda v: page.set_title(v.get_property("window-title") or "Terminal")
        )
        self.tab_view.set_selected_page(page)

    def show_tty_dialog(self):
        TTYDialog(self, self.add_tty_tab).present()

    def add_tty_tab(self, tty_number):
        terminal = ShellixTerminal(self.settings, is_tty=True)
        terminal.connect("child-exited", lambda t, s: self.on_terminal_child_exited(t))
        terminal.spawn_tty(tty_number)

        scrolled = Gtk.ScrolledWindow(child=terminal)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        page = self.tab_view.append(scrolled)
        page.set_title(f"TTY {tty_number}")
        self.tab_view.set_selected_page(page)

    def on_tab_changed(self, tab_view, param):
        term = self.get_current_terminal()
        if term:
            GLib.idle_add(self._focus_current_terminal, term)

    def _focus_current_terminal(self, term):
        term.grab_focus()
        return GLib.SOURCE_REMOVE

    def get_current_terminal(self):
        page = self.tab_view.get_selected_page()
        if page and page.get_child():
            return page.get_child().get_child()
        return None

    def close_current_tab(self):
        page = self.tab_view.get_selected_page()
        if page: 
            self.tab_view.close_page(page)

    def on_page_close_request(self, tab_view, page):
        if tab_view.get_n_pages() <= 1: 
            self.close()
        else:
            tab_view.close_page_finish(page, True)
        return True

    def on_terminal_child_exited(self, terminal):
        for i in range(self.tab_view.get_n_pages()):
            page = self.tab_view.get_nth_page(i)
            if page.get_child().get_child() == terminal:
                self.tab_view.close_page(page)
                break

    def on_close_request(self, window):
        if self._stats_timer_id:
            GLib.source_remove(self._stats_timer_id)
            self._stats_timer_id = None

        w, h = self.get_default_size()
        if w > 0 and h > 0:
            self.settings["window_width"] = w
            self.settings["window_height"] = h

        self.settings["is_maximized"] = self.is_maximized()
        Config.save_settings(self.settings)
        return False

    def on_setup_tab_menu(self, tab_view, page):
        menu = Gio.Menu()
        menu.append(_("Новая вкладка"), "win.new_tab")
        menu.append(_("Закрыть"), "win.close_tab")
        tab_view.set_menu_model(menu)

    def do_copy(self):
        term = self.get_current_terminal()
        if term: 
            term.copy_clipboard()

    def do_paste(self):
        term = self.get_current_terminal()
        if term: 
            term.paste_clipboard()

    def show_preferences(self):
        PreferencesWindow(self, self.settings, Config.save_settings).present()

    def on_settings_reloaded(self, new_settings):
        self.settings = new_settings
        for i in range(self.tab_view.get_n_pages()):
            term = self.tab_view.get_nth_page(i).get_child().get_child()
            if hasattr(term, 'apply_settings'): 
                term.apply_settings(new_settings)


class ShellixApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=Config.APP_ID, 
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.set_accels_for_action("win.new_tab", ["<Control>t"])
        self.set_accels_for_action("win.close_tab", ["<Control>w"])
        self.set_accels_for_action("win.copy", ["<Control><Shift>c"])
        self.set_accels_for_action("win.paste", ["<Control><Shift>v"])
        self.set_accels_for_action("app.new_window", ["<Control>n"])
        self.set_accels_for_action("win.preferences", ["<Control>comma"])
        self.set_accels_for_action("win.about", ["F1"])
        self.set_accels_for_action("win.connect_tty", ["<Control>y"])

        action = Gio.SimpleAction.new("new_window", None)
        action.connect("activate", lambda a, p: self.activate_with_path(None))
        self.add_action(action)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()
        target_path = None

        if len(args) > 1:
            arg = args[1]
            if arg.startswith("file://"):
                arg = arg.replace("file://", "", 1)

            potential_path = unquote(arg)
            if os.path.isdir(potential_path):
                target_path = potential_path
            elif os.path.isfile(potential_path):
                target_path = os.path.dirname(potential_path)

        self.activate_with_path(target_path)
        return 0

    def do_activate(self):
        self.activate_with_path(None)

    def activate_with_path(self, path):
        win = ShellixWindow(self, settings=Config.load_settings(), initial_path=path)
        win.present()


if __name__ == "__main__":
    set_process_name("Shellix")
    app = ShellixApplication()
    sys.exit(app.run(sys.argv))