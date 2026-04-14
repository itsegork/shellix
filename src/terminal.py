import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import GLib, Gdk, Vte, Pango, Gtk
from config import Config

class ShellixTerminal(Vte.Terminal):
    def __init__(self, settings):
        super().__init__()
        
        self.set_focusable(True)
        self.set_can_focus(True)
        self.set_focus_on_click(True)
        self.set_hexpand(True)
        self.set_vexpand(True)
        
        self.set_encoding("UTF-8")
        self.set_mouse_autohide(True)
        self.apply_settings(settings)
        
        self.setup_internal_style()
        
        GLib.idle_add(self.spawn_shell)

    def setup_internal_style(self):
        css_provider = Gtk.CssProvider()
        css_data = b"""
            vte-terminal {
                padding: 20px;
            }
        """
        css_provider.load_from_data(css_data)
        self.get_style_context().add_provider(
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def apply_settings(self, settings):
        self.settings = settings
        
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
        self.set_cursor_shape(cursor_map.get(
            self.settings.get("cursor_shape", "block"), 
            Vte.CursorShape.BLOCK
        ))
        
        self.set_audible_bell(self.settings.get("enable_audible_bell", False))
        self.setup_colors()

    def setup_colors(self):
        context = self.get_style_context()
        success_fg, fg = context.lookup_color("window_fg_color")
        success_bg, bg = context.lookup_color("window_bg_color")
        
        if not success_fg:
            fg = Gdk.RGBA()
            fg.parse("white")
        if not success_bg:
            bg = Gdk.RGBA()
            bg.parse("#242424")
        self.set_colors(fg, bg, None)

    def spawn_shell(self):
        shell = self.settings.get("default_shell", os.environ.get("SHELL", "/bin/bash"))
        if not os.path.exists(shell):
            shell = "/bin/bash"

        environ = os.environ.copy()
        environ["TERM"] = "xterm-256color"
        environ["COLORTERM"] = "truecolor"
        environ["TERM_PROGRAM"] = "Shellix"
        environ["TERM_PROGRAM_VERSION"] = Config.CURRENT_VERSION
        
        env_list = [f"{k}={v}" for k, v in environ.items()]
        
        self.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.path.expanduser("~"),       # working_directory
            [shell],                       # argv
            env_list,                      # envv
            GLib.SpawnFlags.SEARCH_PATH,   # spawn_flags
            None,                          # child_setup
            None,                          # child_setup_data
            -1,                            # timeout
            None,                          # cancellable
            self.on_spawn_complete,        # callback
            None                           # user_data
        )

    def on_spawn_complete(self, terminal, pid, error, user_data):
        if error:
            print(f"Ошибка запуска Shell: {error.message}")
            return

        self.grab_focus()

    def zoom_in(self):
        self.set_font_scale(self.get_font_scale() + 0.1)
    
    def zoom_out(self):
        self.set_font_scale(max(0.1, self.get_font_scale() - 0.1))
    
    def zoom_reset(self):
        self.set_font_scale(1.0)