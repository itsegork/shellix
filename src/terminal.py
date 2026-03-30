import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Vte', '3.91')

from gi.repository import GLib, Gdk, Vte, Pango
from config import Config

class ShellixTerminal(Vte.Terminal):
    def __init__(self, settings):

        super().__init__()
        
        self.set_encoding("UTF-8")
        self.set_mouse_autohide(True)
        
        self.apply_settings(settings)
        
        GLib.idle_add(self.spawn_shell)
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        
    def apply_settings(self, settings):

        self.settings = settings
        
        self.set_scrollback_lines(self.settings.get("scrollback_lines", 10000))
        
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
        
        env_list = [f"{k}={v}" for k, v in environ.items()]
        
        self.spawn_async(
            Vte.PtyFlags.DEFAULT,
            Config.CONFIG_HOME,
            [shell], 
            env_list,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None, None, -1, None,
            self.on_spawn_complete,
            None
        )

    def on_spawn_complete(self, terminal, pid, error, user_data):
        if error:
            print(f"Error: {error.message}")
            return

        custom_commands = [
            f"alias aboutshellix='echo \"Shellix {Config.CURRENT_VERSION} - Modern Virtual Terminal.\"'\n",
            "clear\n" 
        ]

        for cmd in custom_commands:
            try:
                self.feed_child(cmd.encode('utf-8'))
            except TypeError:
                self.feed_child(cmd.encode('utf-8'), len(cmd))

    def on_spawn_done(self, terminal, pid, error, user_data):
        if error:
            print(f"Ошибка VTE: {error.message}")
            self.feed_child(b"\r\n\x1b[31m[Shellix Error]: Failed to spawn shell\x1b[0m\r\n", -1)

    def zoom_in(self):
        self.set_font_scale(self.get_font_scale() + 0.1)
    
    def zoom_out(self):
        self.set_font_scale(max(0.1, self.get_font_scale() - 0.1))
    
    def zoom_reset(self):
        self.set_font_scale(1.0)