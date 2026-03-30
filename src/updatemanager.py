import threading
import requests
import webbrowser
from gi.repository import Adw, GLib

from config import Config

class UpdateManager:
    def __init__(self, parent_window):
        self.window = parent_window
        self.is_checking = False

    def check(self):
        if self.is_checking:
            return
        
        self.is_checking = True
        self.old_stats = self.window.stats_label.get_label()
        self.window.stats_label.set_label("󰚰 Проверка обновлений...")
        
        threading.Thread(target=self._run_check, daemon=True).start()

    def _run_check(self):
        try:
            url = f'https://api.github.com/repos/{Config.GITHUB_REPO}/releases/latest'
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest = data.get('tag_name', '0.0.0')
                current = Config.CURRENT_VERSION

                if latest > current:
                    GLib.idle_add(self._show_update_toast, data)
                else:
                    GLib.idle_add(self._show_status_toast, "Shellix актуален")
            else:
                GLib.idle_add(self._show_status_toast, "Ошибка сервера GitHub")
                
        except Exception as e:
            print(f"Ошибка проверки обновлений: {e}")
            GLib.idle_add(self._show_status_toast, "Нет связи с GitHub")
        finally:
            self.is_checking = False
            GLib.timeout_add_seconds(3, self._restore_header)

    def _restore_header(self):
        if hasattr(self.window, 'stats_label'):
            self.window.stats_label.set_label(self.old_stats)
        return False

    def _show_update_toast(self, data):
        version = data.get('tag_name', 'новое')
        toast = Adw.Toast.new(f"Доступна версия {version}")
        toast.set_button_label("Открыть GitHub")
        
        toast.connect("button-clicked", lambda t: webbrowser.open(data['html_url']))
        
        if hasattr(self.window, 'add_toast'):
            self.window.add_toast(toast)

    def _show_status_toast(self, message):
        toast = Adw.Toast.new(message)
        if hasattr(self.window, 'add_toast'):
            self.window.add_toast(toast)