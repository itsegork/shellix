import os
import json
import tempfile
from gi.repository import Gio, GLib

class Config:
    APP_ID = "ru.itsegork.shellix"
    APP_NAME = "Shellix"
    CURRENT_VERSION = "1.1.0"
    GITHUB_REPO = "itsegork/shellix"
    
    CONFIG_DIR = os.path.expanduser("~/.config/shellix")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
    
    DEFAULT_SETTINGS = {
        "font": "Adwaita Mono 12",
        "cursor_shape": "block",
        "enable_audible_bell": True,
        "enable_auto_updates": True,
        "default_shell": os.environ.get("SHELL", "/bin/bash"),
        "window_width": 800,
        "window_height": 600,
        "is_maximized": False,
        "show_cpu": True,
        "show_ram": True,
        "show_disk": True,
        "show_net": True,
    }

    _monitor = None
    _on_change_callback = None
    
    @classmethod
    def ensure_config_dir(cls):
        if not os.path.exists(cls.CONFIG_DIR):
            os.makedirs(cls.CONFIG_DIR, exist_ok=True)
    
    @classmethod
    def load_settings(cls):
        cls.ensure_config_dir()
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                validated = cls.DEFAULT_SETTINGS.copy()
                for key, default_val in cls.DEFAULT_SETTINGS.items():
                    if key in settings:
                        val = settings[key]
                        if type(val) is type(default_val):
                            validated[key] = val
                return validated
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
                
        return cls.DEFAULT_SETTINGS.copy()
    
    @classmethod
    def save_settings(cls, new_data):
        current = cls.load_settings()
        current.update(new_data)
        cls.ensure_config_dir()

        try:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=cls.CONFIG_DIR, text=True)
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(current, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, cls.CONFIG_FILE)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    @classmethod
    def watch(cls, callback):
        cls._on_change_callback = callback
        if cls._monitor:
            cls._monitor.cancel()

        try:
            cls.ensure_config_dir()
            if not os.path.exists(cls.CONFIG_FILE):
                cls.save_settings({})

            file = Gio.File.new_for_path(cls.CONFIG_FILE)
            cls._monitor = file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            cls._monitor.connect("changed", cls._on_file_changed)
        except Exception as e:
            print(f"Ошибка инициализации Gio.FileMonitor: {e}")

    @classmethod
    def _on_file_changed(cls, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            GLib.timeout_add(100, cls._reload_and_notify)

    @classmethod
    def _reload_and_notify(cls):
        if cls._on_change_callback:
            cls._on_change_callback(cls.load_settings())
        return False