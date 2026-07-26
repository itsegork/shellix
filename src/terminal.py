import gi
import os
import subprocess

gi.require_version('Gtk', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import GLib, Gdk, Vte, Pango, Gtk, Gio
from config import Config

def _(text):
    return text

class ShellixTerminal(Vte.Terminal):
    def __init__(self, settings, is_tty=False, work_dir=None):
        super().__init__()
        
        self.is_tty = is_tty
        self.settings = settings
        self.work_dir = work_dir or os.path.expanduser("~")
        
        self.set_focusable(True)
        self.set_can_focus(True)
        self.set_focus_on_click(True)
        self.set_hexpand(True)
        self.set_vexpand(True)
        
        self.set_encoding("UTF-8")
        self.set_mouse_autohide(True)
        
        self.apply_settings(settings)
        self.setup_internal_style()
        self.setup_context_menu()

        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll_controller.connect("scroll", self.on_scroll)
        self.add_controller(scroll_controller)

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)
        
        if not self.is_tty:
            GLib.idle_add(self.spawn_shell)

    def setup_internal_style(self):
        css_provider = Gtk.CssProvider()
        padding = "0px" if self.is_tty else "20px"
        css_data = f"vte-terminal {{ padding: {padding}; }}".encode('utf-8')
        
        css_provider.load_from_data(css_data)
        self.get_style_context().add_provider(
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def setup_context_menu(self):
        menu = Gio.Menu.new()
        menu.append(_("Копировать"), "win.copy")
        menu.append(_("Вставить"), "win.paste")
        
        self.context_menu = Gtk.PopoverMenu.new_from_model(menu)
        self.context_menu.set_parent(self)
        self.context_menu.set_has_arrow(False)

        click_gesture = Gtk.GestureClick.new()
        click_gesture.set_button(Gdk.BUTTON_SECONDARY)
        click_gesture.connect("pressed", self.on_right_click)
        self.add_controller(click_gesture)

    def on_right_click(self, gesture, n_press, x, y):
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        
        self.context_menu.set_pointing_to(rect)
        self.context_menu.popup()

    def apply_settings(self, settings):
        self.settings = settings
        
        if self.is_tty:
            self.set_scrollback_lines(0)
            self.set_scroll_on_keystroke(True)
            self.set_scroll_on_output(True)
            font_string = "Monospace 7"
        else:
            self.set_scrollback_lines(self.settings.get("scrollback_lines", 10000))
            self.set_scroll_on_keystroke(True)
            self.set_scroll_on_output(False)
            font_string = self.settings.get("font", "Adwaita Mono 12")
            
        font_desc = Pango.FontDescription.from_string(font_string)
        self.set_font(font_desc)
        
        cursor_map = {
            "block": Vte.CursorShape.BLOCK,
            "ibeam": Vte.CursorShape.IBEAM,
            "underline": Vte.CursorShape.UNDERLINE
        }
        
        shape = Vte.CursorShape.BLOCK if self.is_tty else \
                cursor_map.get(self.settings.get("cursor_shape", "block"), Vte.CursorShape.BLOCK)
        self.set_cursor_shape(shape)
        
        self.set_audible_bell(self.settings.get("enable_audible_bell", False))
        self.setup_colors()

    def setup_colors(self):
        if self.is_tty:
            fg = Gdk.RGBA(); fg.parse("#aaaaaa")
            bg = Gdk.RGBA(); bg.parse("#000000")
            self.set_colors(fg, bg, None)
        else:
            context = self.get_style_context()
            success_fg, fg = context.lookup_color("window_fg_color")
            success_bg, bg = context.lookup_color("window_bg_color")
            
            if not success_fg:
                fg = Gdk.RGBA(); fg.parse("white")
            if not success_bg:
                bg = Gdk.RGBA(); bg.parse("#242424")
            self.set_colors(fg, bg, None)

    def spawn_shell(self):
        shell = self.settings.get("default_shell", os.environ.get("SHELL", "/bin/bash"))
        if not os.path.exists(shell):
            shell = "/bin/bash"

        cwd = self.work_dir if os.path.isdir(self.work_dir) else os.path.expanduser("~")

        environ = os.environ.copy()
        environ["TERM"] = "xterm-256color"
        environ["COLORTERM"] = "truecolor"
        environ["TERM_PROGRAM"] = "Shellix"
        environ["TERM_PROGRAM_VERSION"] = Config.CURRENT_VERSION
        
        env_list = [f"{k}={v}" for k, v in environ.items()]
        
        self.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd,
            [shell],
            env_list,
            GLib.SpawnFlags.SEARCH_PATH,
            None, None, -1, None,
            self.on_spawn_complete,
            None
        )

    def spawn_tty(self, tty_number):
        environ = os.environ.copy()
        environ["TERM"] = "linux"
        env_list = [f"{k}={v}" for k, v in environ.items()]
        cmd = f"systemctl start getty@tty{tty_number}.service 2>/dev/null; exec conspy {tty_number}"
        argv = ["pkexec", "sh", "-c", cmd]

        self.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.path.expanduser("~"),
            argv,
            env_list,
            GLib.SpawnFlags.SEARCH_PATH,
            None, None, -1, None,
            self.on_spawn_complete,
            None
        )

    def on_spawn_complete(self, terminal, pid, error, user_data):
        if error:
            print(f"Ошибка запуска: {error.message}")
            return
        self.grab_focus()

    def zoom_in(self):
        self.set_font_scale(self.get_font_scale() + 0.1)
    
    def zoom_out(self):
        self.set_font_scale(max(0.1, self.get_font_scale() - 0.1))
    
    def zoom_reset(self):
        self.set_font_scale(1.0)

    def on_scroll(self, controller, dx, dy):
        state = controller.get_current_event_state()
        if state & Gdk.ModifierType.CONTROL_MASK:
            if dy < 0:
                self.zoom_in()
            elif dy > 0:
                self.zoom_out()
            return True
        return False

    def on_key_pressed(self, controller, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK:
            if keyval in (Gdk.KEY_equal, Gdk.KEY_plus, Gdk.KEY_KP_Add):
                self.zoom_in()
                return True
            elif keyval in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
                self.zoom_out()
                return True
            elif keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
                self.zoom_reset()
                return True
        return False