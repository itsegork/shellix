import os
import json
from gi.repository import Gio, GLib

class Config:
    APP_ID = "ru.itsegork.shellix"
    APP_NAME = "Shellix"
    CURRENT_VERSION = "1.0.0"
    GITHUB_REPO = "itsegork/shellix"
    
    CONFIG_DIR = os.path.expanduser("~/.config/shellix")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
    
    DEFAULT_SETTINGS = {
        "font": "Adwaita Mono 12",
        "cursor_shape": "block",
        "enable_audible_bell": True,
        "default_shell": os.environ.get("SHELL", "/bin/bash")
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
                with open(cls.CONFIG_FILE, 'r') as f:
                    settings = json.load(f)
                    validated = cls.DEFAULT_SETTINGS.copy()
                    for key, value in settings.items():
                        if key in validated:
                            v_type = type(validated[key])
                            if isinstance(value, v_type) and type(value) is v_type:
                                validated[key] = value
                    return validated
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
                return cls.DEFAULT_SETTINGS.copy()
        return cls.DEFAULT_SETTINGS.copy()
    
    @staticmethod
    def save_settings(new_data):
        current = Config.load_settings()
        current.update(new_data)
        
        Config.ensure_config_dir()
        try:
            with open(Config.CONFIG_FILE, 'w') as f:
                json.dump(current, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    @classmethod
    def watch(cls, callback):
        cls._on_change_callback = callback
        try:
            file = Gio.File.new_for_path(cls.CONFIG_FILE)
            cls._monitor = file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            cls._monitor.connect("changed", cls._on_file_changed)
        except Exception:
            pass

    @classmethod
    def _on_file_changed(cls, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            GLib.timeout_add(100, cls._reload_and_notify)

    @classmethod
    def _reload_and_notify(cls):
        if cls._on_change_callback:
            settings = cls.load_settings()
            cls._on_change_callback(settings)
        return False