import gi
import sys
import psutil
import time

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import Adw, Gtk, Gio, Gdk, GLib
from config import Config
from terminal import ShellixTerminal
from preferences import PreferencesWindow
from info import Info
from updatemanager import UpdateManager

class ShellixWindow(Adw.ApplicationWindow):
    def __init__(self, app, settings):
        super().__init__(application=app)
        
        self.settings = settings
        self.set_title("Shellix")
        self.set_default_size(1000, 650)
        
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        
        self.update_manager = UpdateManager(self)
        
        self.setup_ui()
        self.setup_actions()
        self.setup_shortcuts()
        
        Config.watch(self.on_settings_reloaded)
        self.new_tab()
        
        GLib.timeout_add_seconds(2, self.update_system_stats)

    def setup_ui(self):
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        self.header = Adw.HeaderBar()
        
        self.stats_label = Gtk.Label(label="Загрузка...")
        self.stats_label.add_css_class("title")
        self.stats_label.set_selectable(False)
        self.header.set_title_widget(self.stats_label)
        
        menu = Gio.Menu.new()
        menu.append("Проверить обновления", "win.check_updates")
        menu.append("Настройки", "win.preferences")
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

        self.tab_view.set_hexpand(True)
        self.tab_view.set_vexpand(True)
        main_box.append(self.tab_view)

        self.apply_clean_styles()

    def add_toast(self, toast):
        self.toast_overlay.add_toast(toast)

    def update_system_stats(self):
        if getattr(self.update_manager, 'is_checking', False):
            return True

        try:
            cpu = psutil.cpu_percent()
            
            vm = psutil.virtual_memory()
            ram_used = vm.used / (1024**3)
            ram_total = vm.total / (1024**3)
            
            du = psutil.disk_usage('/')
            disk_used = du.used / (1024**3)
            disk_total = du.total / (1024**3)
            
            net_io = psutil.net_io_counters()
            now = time.time()
            elapsed = now - self.last_time
            dl = (net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed / 1024
            ul = (net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed / 1024
            
            self.last_net_io = net_io
            self.last_time = now

            stats = (
                f"  {cpu}%  "
                f"󰘚  {ram_used:.1f}/{ram_total:.1f} GB  "
                f"󰋊  {disk_used:.0f}/{disk_total:.0f} GB  "
                f"󰓅  {dl:.1f}↓ {ul:.1f}↑ КБ/с"
            )
            self.stats_label.set_label(stats)
            
        except Exception:
            self.stats_label.set_label("Shellix")
        
        return True

    def apply_clean_styles(self):
        provider = Gtk.CssProvider()
        css = """
            headerbar { border-bottom: none; box-shadow: none; }
            headerbar label.title { 
                font-feature-settings: "tnum"; 
            }
            tabbar { border: none; background-color: @window_bg_color; }
            scrolledwindow, tabview { border: none; background-color: transparent; }
            tab { border: none; box-shadow: none; outline: none; }
            tabbox { outline: none; }
        """
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def setup_shortcuts(self):
        key_controller = Gtk.EventControllerKey.new()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

    def on_key_pressed(self, controller, keyval, keycode, state):
        state = state & Gtk.accelerator_get_default_mod_mask()
        if state == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            if keyval == Gdk.KEY_T: self.activate_action("win.new_tab", None); return True
            if keyval == Gdk.KEY_W: self.activate_action("win.close_tab", None); return True
            if keyval == Gdk.KEY_C: self.do_copy(); return True
            if keyval == Gdk.KEY_V: self.do_paste(); return True

        if state == Gdk.ModifierType.CONTROL_MASK:
            if keyval in [Gdk.KEY_plus, Gdk.KEY_equal]: self.do_zoom_in(); return True
            if keyval == Gdk.KEY_minus: self.do_zoom_out(); return True
            if keyval == Gdk.KEY_0: self.do_zoom_reset(); return True
            if keyval == Gdk.KEY_comma: self.show_preferences(); return True
            if keyval == Gdk.KEY_Page_Down: self.tab_view.select_next_page(); return True
            if keyval == Gdk.KEY_Page_Up: self.tab_view.select_previous_page(); return True
        return False

    def setup_actions(self):
        actions = {
            "new_tab": self.new_tab,
            "close_tab": self.close_current_tab,
            "next_tab": lambda: self.tab_view.select_next_page(),
            "prev_tab": lambda: self.tab_view.select_previous_page(),
            "preferences": self.show_preferences,
            "about": lambda: Info.__init__(self, parent=self),
            "check_updates": lambda: self.update_manager.check(),
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda a, p, cb=callback: cb())
            self.add_action(action)

    def new_tab(self):
        terminal = ShellixTerminal(self.settings)
        terminal.connect("child-exited", self.on_terminal_child_exited)
        terminal.set_hexpand(True)
        terminal.set_vexpand(True)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(terminal)
        page = self.tab_view.append(scrolled)
        page.set_title("Terminal")
        terminal.connect("window-title-changed", lambda vte: page.set_title(vte.get_window_title() or "Terminal"))
        self.tab_view.set_selected_page(page)
        terminal.grab_focus()

    def get_current_terminal(self):
        page = self.tab_view.get_selected_page()
        if page: return page.get_child().get_child()
        return None

    def on_page_close_request(self, tab_view, page):
        if tab_view.get_n_pages() <= 1: self.get_application().quit(); return True 
        return False 

    def close_current_tab(self):
        page = self.tab_view.get_selected_page()
        if page: self.tab_view.close_page(page)

    def on_terminal_child_exited(self, terminal, status):
        for i in range(self.tab_view.get_n_pages()):
            page = self.tab_view.get_nth_page(i)
            if page.get_child().get_child() == terminal:
                self.tab_view.close_page(page)
                break

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

    def do_zoom_in(self):
        term = self.get_current_terminal()
        if term: term.zoom_in()

    def do_zoom_out(self):
        term = self.get_current_terminal()
        if term: term.zoom_out()

    def do_zoom_reset(self):
        term = self.get_current_terminal()
        if term: term.zoom_reset()

    def show_preferences(self):
        prefs = PreferencesWindow(self, self.settings, Config.save_settings)
        prefs.present()

    def on_settings_reloaded(self, new_settings):
        self.settings = new_settings
        for i in range(self.tab_view.get_n_pages()):
            page = self.tab_view.get_nth_page(i)
            terminal = page.get_child().get_child()
            if isinstance(terminal, ShellixTerminal):
                terminal.apply_settings(new_settings)

class ShellixApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=Config.APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        settings = Config.load_settings()
        win = self.props.active_window
        if not win: win = ShellixWindow(self, settings)
        win.present()

def main():
    app = ShellixApplication()
    return app.run(sys.argv)

if __name__ == "__main__":
    main()