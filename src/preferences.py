import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Adw, Gtk, PangoCairo

class PreferencesWindow(Adw.Window):
    def __init__(self, parent, current_settings, save_callback):
        super().__init__(transient_for=parent, modal=True)
        
        self.set_title("Настройки Shellix")
        self.set_default_size(480, -1)
        self.save_callback = save_callback
        self.settings = current_settings

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        header = Adw.HeaderBar()
        main_box.append(header)

        page = Adw.PreferencesPage()
        main_box.append(page)

        def configure_suffix(widget):
            widget.set_valign(Gtk.Align.CENTER)
            widget.set_halign(Gtk.Align.END)
            widget.set_hexpand(False)
            if isinstance(widget, Gtk.DropDown):
                widget.set_size_request(220, -1)
            return widget

        group = Adw.PreferencesGroup(title="Терминал")
        page.add(group)

        bell_row = Adw.ActionRow(title="Звуковой сигнал")
        self.bell_switch = Gtk.Switch()
        self.bell_switch.set_active(self.settings.get('enable_audible_bell', False))
        bell_row.add_suffix(configure_suffix(self.bell_switch))
        group.add(bell_row)

        update_group = Adw.PreferencesGroup(title="Обновления")
        page.add(update_group)

        update_row = Adw.ActionRow(title="Автоматическая проверка")
        update_row.set_subtitle("Проверять наличие новых версий при запуске")
        self.update_switch = Gtk.Switch()
        self.update_switch.set_active(self.settings.get('enable_auto_updates', True))
        update_row.add_suffix(configure_suffix(self.update_switch))
        update_group.add(update_row)

        cursor_row = Adw.ActionRow(title="Вид курсора")
        self.cursor_names = ["Block", "I-Beam", "Underline"]
        self.cursor_values = ["block", "ibeam", "underline"]
        
        self.cursor_drop = Gtk.DropDown.new_from_strings(self.cursor_names)
        
        current_cursor = self.settings.get('cursor_shape', 'block')
        if current_cursor in self.cursor_values:
            self.cursor_drop.set_selected(self.cursor_values.index(current_cursor))
            
        cursor_row.add_suffix(configure_suffix(self.cursor_drop))
        group.add(cursor_row)

        shell_row = Adw.EntryRow(title="Путь к оболочке")
        shell_row.set_text(self.settings.get('default_shell', "/bin/bash"))
        self.shell_entry = shell_row
        group.add(shell_row)

        font_group = Adw.PreferencesGroup(title="Шрифт")
        page.add(font_group)

        font_row = Adw.ActionRow(title="Шрифт системы")
        mono_fonts = self.get_system_mono_fonts()
        self.font_drop = Gtk.DropDown.new_from_strings(mono_fonts)
        
        current_font_full = self.settings.get('font', "Monospace 12")
        current_font_name = " ".join(current_font_full.split()[:-1]) 
        
        try:
            self.font_drop.set_selected(mono_fonts.index(current_font_name))
        except ValueError: pass

        font_row.add_suffix(configure_suffix(self.font_drop))
        font_group.add(font_row)

        size_row = Adw.ActionRow(title="Размер")
        sizes = ["8", "9", "10", "11", "12", "13", "14", "16", "18", "20", "24"]
        self.size_drop = Gtk.DropDown.new_from_strings(sizes)
        
        current_size = current_font_full.split()[-1]
        try:
            self.size_drop.set_selected(sizes.index(current_size))
        except ValueError: self.size_drop.set_selected(4)

        size_row.add_suffix(configure_suffix(self.size_drop))
        font_group.add(size_row)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_margin_end(18)
        btn_box.set_halign(Gtk.Align.END)
        
        cancel_btn = Gtk.Button(label="Отмена")
        cancel_btn.connect("clicked", lambda b: self.close())
        
        save_btn = Gtk.Button(label="Сохранить")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.on_save_clicked)
        
        btn_box.append(cancel_btn)
        btn_box.append(save_btn)
        main_box.append(btn_box)

    def get_system_mono_fonts(self):
        font_map = PangoCairo.FontMap.get_default()
        families = font_map.list_families()
        mono_fonts = [f.get_name() for f in families if f.is_monospace()]
        mono_fonts.sort()
        return mono_fonts if mono_fonts else ["Monospace"]

    def on_save_clicked(self, button):
        font_name = self.font_drop.get_selected_item().get_string()
        font_size = self.size_drop.get_selected_item().get_string()
        
        cursor_idx = self.cursor_drop.get_selected()
        selected_cursor = self.cursor_values[cursor_idx]

        new_data = {
            "enable_audible_bell": bool(self.bell_switch.get_active()),
            "enable_auto_updates": bool(self.update_switch.get_active()),
            "font": f"{font_name} {font_size}",
            "default_shell": str(self.shell_entry.get_text()),
            "cursor_shape": selected_cursor
        }

        self.save_callback(new_data)
        self.close()