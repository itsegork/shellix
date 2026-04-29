from gi.repository import Nautilus, GObject
import os

class ShellixMenuExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        pass

    def _open_shellix(self, menu, file):
        path = file.get_location().get_path()
        os.system(f"shellix '{path}' &")

    def get_file_items(self, *args):
        files = args[-1]
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
        file = args[-1]
        item = Nautilus.MenuItem(
            name="Shellix::OpenTerminalBackground",
            label="Открыть в Shellix",
            tip="Открыть текущую папку в терминале Shellix",
            icon="ru.itsegork.shellix"
        )
        item.connect("activate", self._open_shellix, file)
        return [item]