import subprocess
from gi.repository import Nautilus, GObject


class ShellixMenuExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def _open_shellix(self, menu, file):
        location = file.get_location()
        if not location:
            return

        path = location.get_path()
        if path:
            try:
                subprocess.Popen(["shellix", path], start_new_session=True)
            except Exception:
                try:
                    subprocess.Popen(["python3", "-m", "shellix", path], start_new_session=True)
                except Exception:
                    pass

    def get_file_items(self, *args):
        files = args[-1] if args else []
        if len(files) != 1 or not files[0].is_directory():
            return []

        item = Nautilus.MenuItem(
            name="Shellix::OpenTerminal",
            label="Открыть в Shellix",
            tip="Открыть эту папку в терминале Shellix",
            icon="ru.itsegork.shellix"
        )
        item.connect("activate", self._open_shellix, files[0])
        return [item]

    def get_background_items(self, *args):
        file = args[-1] if args else None
        if not file:
            return []

        item = Nautilus.MenuItem(
            name="Shellix::OpenTerminalBackground",
            label="Открыть в Shellix",
            tip="Открыть текущую папку в терминале Shellix",
            icon="ru.itsegork.shellix"
        )
        item.connect("activate", self._open_shellix, file)
        return [item]