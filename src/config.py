import os
import json
import tempfile
import logging
import gettext
import locale
from gi.repository import Gio, GLib

logger = logging.getLogger("Shellix")

class Config:
    APP_ID = "ru.itsegork.shellix"
    APP_NAME = "Shellix"
    CURRENT_VERSION = "1.1.1"
    GITHUB_REPO = "itsegork/shellix"
    GETTEXT_PACKAGE = "shellix"

    CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "shellix")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

    DEFAULT_SETTINGS = {
        "font": "Adwaita Mono 12",
        "cursor_shape": "block",
        "enable_audible_bell": True,
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
    def get_locale_dir(cls) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        parent_dir = os.path.dirname(current_dir)
        possible_paths = [
            os.path.join(parent_dir, "locale"),
            os.path.join(current_dir, "locale"),
            "/usr/share/locale"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return os.path.join(parent_dir, "locale")

    @classmethod
    def setup_i18n(cls):
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error as e:
            logger.warning(f"Failed to set system locale: {e}")

        locale_dir = cls.get_locale_dir()
        
        gettext.bindtextdomain(cls.GETTEXT_PACKAGE, locale_dir)
        gettext.textdomain(cls.GETTEXT_PACKAGE)
        
        gettext.install(cls.GETTEXT_PACKAGE, locale_dir)
        logger.info(f"Localization initialized (locale_dir: {locale_dir})")

    @classmethod
    def ensure_config_dir(cls):
        if not os.path.exists(cls.CONFIG_DIR):
            os.makedirs(cls.CONFIG_DIR, exist_ok=True)

    @classmethod
    def load_settings(cls) -> dict:
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
                logger.error(f"Error loading settings: {e}")

        return cls.DEFAULT_SETTINGS.copy()

    @classmethod
    def save_settings(cls, new_data: dict):
        current = cls.load_settings()
        current.update(new_data)
        cls.ensure_config_dir()

        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=cls.CONFIG_DIR, text=True)
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(current, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, cls.CONFIG_FILE)
            tmp_path = None
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

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
            logger.error(f"Error initializing Gio.FileMonitor: {e}")

    @classmethod
    def _on_file_changed(cls, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            GLib.timeout_add(100, cls._reload_and_notify)

    @classmethod
    def _reload_and_notify(cls) -> bool:
        if cls._on_change_callback:
            cls._on_change_callback(cls.load_settings())
        return GLib.SOURCE_REMOVE