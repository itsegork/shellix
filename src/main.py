import gi
import sys
import psutil
import time
import ctypes
import ctypes.util

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import Adw, Gtk, Gio, Gdk, GLib
from config import Config
from terminal import ShellixTerminal
from preferences import PreferencesWindow
from info import Info
from updatemanager import UpdateManager

def set_process_name(name):
    try:
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        buff = ctypes.create_string_buffer(name.encode('utf-8'), 16)
        libc.prctl(15, ctypes.byref(buff), 0, 0, 0)
    except Exception:
        pass

class TTYDialog(Adw.Window):
    def __init__(self, parent, callback):
        super().__init__(transient_for=parent, modal=True)
        self.set_title("Подключение к TTY")
        self.set_default_size(300, -1)
        self.callback = callback

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_end(18)
        self.set_content(content)

        label = Gtk.Label(label="Введите номер системного TTY (1-6):")
        content.append(label)

        self.entry = Gtk.SpinButton.new_with_range(1, 6, 1)
        self.entry.set_value(1)
        content.append(self.entry)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(6)
        
        cancel_btn = Gtk.Button(label="Отмена")
        cancel_btn.connect("clicked", lambda b: self.close())
        
        connect_btn = Gtk.Button(label="Подключиться")
        connect_btn.add_css_class("suggested-action")
        connect_btn.connect("clicked", self.on_connect_clicked)
        
        btn_box.append(cancel_btn)
        btn_box.append(connect_btn)
        content.append(btn_box)

    def on_connect_clicked(self, btn):
        tty_num = int(self.entry.get_value())
        self.callback(tty_num)
        self.close()

class ShellixWindow(Adw.ApplicationWindow):
    def __init__(self, app, settings):
        super().__init__(application=app)
        
        self.settings = settings
        self.set_title(Config.APP_NAME)
        
        self.set_default_size(
            self.settings.get("window_width", 800), 
            self.settings.get("window_height", 600)
        )
        
        if self.settings.get("is_maximized"):
            self.maximize()
            
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        
        self.setup_ui()
        self.updatemanager = UpdateManager(self)
        self.setup_actions()
        
        Config.watch(self.on_settings_reloaded)
        self.new_tab()
        
        self.connect("close-request", self.on_close_request)
        GLib.timeout_add_seconds(2, self.update_system_stats)
        GLib.timeout_add_seconds(10, self.updatemanager.check)

    def setup_ui(self):
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)
        self.add_toast = self.toast_overlay.add_toast

        self.header = Adw.HeaderBar()
        self.stats_label = Gtk.Label(label="Загрузка...")
        self.stats_label.add_css_class("title")
        self.header.set_title_widget(self.stats_label)
        
        menu = Gio.Menu.new()
        menu.append("Новое окно", "app.new_window")
        menu.append("Проверить обновления", "win.check_updates")
        menu.append("Настройки", "win.preferences")
        menu.append("Подключиться к TTY (UNSTABLE)", "win.connect_tty")
        menu.append("О программе", "win.about")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        self.header.pack_end(menu_button)
        main_box.append(self.header)

        self.tab_view = Adw.TabView()
        self.tab_view.connect("close-page", self.on_page_close_request)
        self.tab_view.connect("setup-menu", self.on_setup_tab_menu)

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
            "new_tab": self.new_tab,
            "close_tab": self.close_current_tab,
            "preferences": self.show_preferences,
            "about": lambda: Info(self),
            "check_updates": lambda: self.updatemanager.check(manual=True),
            "connect_tty": self.show_tty_dialog,
            "copy": self.do_copy,
            "paste": self.do_paste
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda a, p, cb=callback: cb())
            self.add_action(action)

    def update_system_stats(self):
        if getattr(self.updatemanager, 'is_checking', False):
            return True
        try:
            cpu = psutil.cpu_percent()
            vm = psutil.virtual_memory()
            du = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()
            now = time.time()
            elapsed = max(now - self.last_time, 0.1)
            dl = (net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed / 1024
            ul = (net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed / 1024
            self.last_net_io = net_io
            self.last_time = now

            stats = (f"  {cpu}%  󰘚  {vm.used/(1024**3):.1f}/{vm.total/(1024**3):.1f} GB  "
                     f"󰋊  {du.used/(1024**3):.0f}/{du.total/(1024**3):.0f} GB  "
                     f"󰓅  {dl:.1f}↓ {ul:.1f}↑ КБ/с")
            self.stats_label.set_label(stats)
        except Exception:
            self.stats_label.set_label("Shellix")
        return True

    def apply_clean_styles(self):
        provider = Gtk.CssProvider()
        css = """
            headerbar { border-bottom: none; box-shadow: none; }
            headerbar label.title { font-feature-settings: "tnum"; }
            tabbar { border: none; background-color: @window_bg_color; }
            scrolledwindow, tabview { border: none; background-color: transparent; }
        """
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def new_tab(self):
        terminal = ShellixTerminal(self.settings, is_tty=False)
        terminal.connect("child-exited", lambda t, s: self.on_terminal_child_exited(t))
        scrolled = Gtk.ScrolledWindow(child=terminal)
        page = self.tab_view.append(scrolled)
        page.set_title("Terminal")
        terminal.connect("window-title-changed", lambda v: page.set_title(v.get_property("window-title") or "Terminal"))
        self.tab_view.set_selected_page(page)
        terminal.grab_focus()

    def show_tty_dialog(self):
        dialog = TTYDialog(self, self.add_tty_tab)
        dialog.present()

    def add_tty_tab(self, tty_number):
        terminal = ShellixTerminal(self.settings, is_tty=True)
        terminal.connect("child-exited", lambda t, s: self.on_terminal_child_exited(t))
        
        terminal.spawn_tty(tty_number)
        
        scrolled = Gtk.ScrolledWindow(child=terminal)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        
        page = self.tab_view.append(scrolled)
        page.set_title(f"TTY {tty_number}")
        
        self.tab_view.set_selected_page(page)
        terminal.grab_focus()

    def get_current_terminal(self):
        page = self.tab_view.get_selected_page()
        return page.get_child().get_child() if page else None

    def close_current_tab(self):
        page = self.tab_view.get_selected_page()
        if page: self.tab_view.close_page(page)

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
        w, h = self.get_default_size()
        self.settings.update({"window_width": w, "window_height": h, "is_maximized": self.is_maximized()})
        Config.save_settings(self.settings)
        return False

    def on_setup_tab_menu(self, tab_view, page):
        menu = Gio.Menu()
        menu.append("Новая вкладка", "win.new_tab")
        menu.append("Закрыть", "win.close_tab")
        tab_view.set_menu_model(menu)

    def do_copy(self):
        term = self.get_current_terminal()
        if term: term.copy_clipboard()

    def do_paste(self):
        term = self.get_current_terminal()
        if term: term.paste_clipboard()

    def show_preferences(self):
        PreferencesWindow(self, self.settings, Config.save_settings).present()

    def on_settings_reloaded(self, new_settings):
        self.settings = new_settings
        for i in range(self.tab_view.get_n_pages()):
            term = self.tab_view.get_nth_page(i).get_child().get_child()
            if hasattr(term, 'apply_settings'): term.apply_settings(new_settings)

class ShellixApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=Config.APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self):
        Adw.Application.do_startup(self)
        
        self.set_accels_for_action("win.new_tab", ["<Control>t"])
        self.set_accels_for_action("win.close_tab", ["<Control>w"])
        self.set_accels_for_action("win.copy", ["<Control><Shift>c"])
        self.set_accels_for_action("win.paste", ["<Control><Shift>v"])
        self.set_accels_for_action("app.new_window", ["<Control>n"])
        self.set_accels_for_action("win.preferences", ["<Control>comma"])
        self.set_accels_for_action("win.check_updates", ["<Control>u"])
        self.set_accels_for_action("win.about", ["F1"])

        action = Gio.SimpleAction.new("new_window", None)
        action.connect("activate", lambda a, p: self.do_activate())
        self.add_action(action)

    def do_activate(self):
        win = ShellixWindow(self, settings=Config.load_settings())
        win.present()

if __name__ == "__main__":
    set_process_name("Shellix")
    app = ShellixApplication()
    app.run(sys.argv)