import logging
import gi
from i18n import _, setup_i18n

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Adw, Gtk, PangoCairo
from config import Config

logger = logging.getLogger("Shellix")

class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, parent, current_settings: dict, save_callback):
        super().__init__(transient_for=parent, modal=True)

        self.set_title(_("Настройки Shellix"))
        self.set_default_size(500, 600)
        self.save_callback = save_callback
        self.settings = current_settings.copy()

        page = Adw.PreferencesPage()
        page.set_title(_("Основные"))
        page.set_icon_name("preferences-system-symbolic")
        self.add(page)

        terminal_group = Adw.PreferencesGroup(
            title=_("Терминал"),
            description=_("Параметры работы эмулятора терминала")
        )
        page.add(terminal_group)

        self.bell_row = Adw.SwitchRow(
            title=_("Звуковой сигнал"),
            subtitle=_("Использовать системный динамик при завершении задач")
        )
        self.bell_row.set_active(self.settings.get('enable_audible_bell', False))
        terminal_group.add(self.bell_row)

        self.cursor_values = ["block", "ibeam", "underline"]
        cursor_names = [_("Блок (Block)"), _("Вертикальная черта (I-Beam)"), _("Подчеркивание (Underline)")]

        cursor_model = Gtk.StringList.new(cursor_names)
        self.cursor_row = Adw.ComboRow(
            title=_("Вид курсора"),
            model=cursor_model
        )
        current_cursor = self.settings.get('cursor_shape', 'block')
        if current_cursor in self.cursor_values:
            self.cursor_row.set_selected(self.cursor_values.index(current_cursor))
        terminal_group.add(self.cursor_row)

        self.shell_row = Adw.EntryRow(title=_("Путь к оболочке"))
        self.shell_row.set_text(self.settings.get('default_shell', "/bin/bash"))
        terminal_group.add(self.shell_row)

        font_group = Adw.PreferencesGroup(title=_("Шрифт"))
        page.add(font_group)

        mono_fonts = self.get_system_mono_fonts()
        font_model = Gtk.StringList.new(mono_fonts)
        self.font_row = Adw.ComboRow(
            title=_("Шрифт системы"),
            model=font_model
        )

        current_font_full = self.settings.get('font', "Monospace 12")
        font_parts = current_font_full.split()
        current_font_name = " ".join(font_parts[:-1]) if len(font_parts) > 1 else "Monospace"
        current_size = font_parts[-1] if font_parts else "12"

        try:
            self.font_row.set_selected(mono_fonts.index(current_font_name))
        except ValueError:
            pass
        font_group.add(self.font_row)

        self.sizes = ["8", "9", "10", "11", "12", "13", "14", "16", "18", "20", "24"]
        size_model = Gtk.StringList.new(self.sizes)
        self.size_row = Adw.ComboRow(
            title=_("Размер шрифта"),
            model=size_model
        )

        try:
            self.size_row.set_selected(self.sizes.index(current_size))
        except ValueError:
            self.size_row.set_selected(4)

        font_group.add(self.size_row)

        header_group = Adw.PreferencesGroup(
            title=_("Панель мониторинга"),
            description=_("Настройка показателей системы в верхней части окна")
        )
        page.add(header_group)

        self.metric_rows = {}
        metrics = [
            ("show_cpu", _("Загрузка ЦП"), _("Процент использования процессора")),
            ("show_ram", _("Оперативная память"), _("Занятая и доступная ОЗУ")),
            ("show_disk", _("Диск"), _("Занятый объем на накопителе")),
            ("show_net", _("Сетевая активность"), _("Скорость входящего и исходящего трафика"))
        ]

        for key, title, subtitle in metrics:
            row = Adw.SwitchRow(title=title, subtitle=subtitle)
            row.set_active(self.settings.get(key, True))
            header_group.add(row)
            self.metric_rows[key] = row

        self.connect("close-request", self.on_window_close)

    def get_system_mono_fonts(self):
        font_map = PangoCairo.FontMap.get_default()
        families = font_map.list_families()
        mono_fonts = [f.get_name() for f in families if f.is_monospace()]
        mono_fonts.sort()
        return mono_fonts if mono_fonts else ["Monospace"]

    def on_window_close(self, window):
        font_model = self.font_row.get_model()
        selected_font_idx = self.font_row.get_selected()

        if selected_font_idx != Gtk.INVALID_LIST_POSITION:
            font_name = font_model.get_string(selected_font_idx)
        else:
            font_name = "Monospace"

        size_idx = self.size_row.get_selected()
        font_size = self.sizes[size_idx] if 0 <= size_idx < len(self.sizes) else "12"

        cursor_idx = self.cursor_row.get_selected()
        selected_cursor = self.cursor_values[cursor_idx] if 0 <= cursor_idx < len(self.cursor_values) else "block"

        default_shell_path = str(self.shell_row.get_text()).strip() or "/bin/bash"

        new_data = {
            "enable_audible_bell": bool(self.bell_row.get_active()),
            "cursor_shape": selected_cursor,
            "default_shell": default_shell_path,
            "font": f"{font_name} {font_size}",
            "show_cpu": bool(self.metric_rows["show_cpu"].get_active()),
            "show_ram": bool(self.metric_rows["show_ram"].get_active()),
            "show_disk": bool(self.metric_rows["show_disk"].get_active()),
            "show_net": bool(self.metric_rows["show_net"].get_active()),
        }

        logger.info("Saving updated settings...")
        self.save_callback(new_data)
        return False