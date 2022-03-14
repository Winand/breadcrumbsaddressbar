import os
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt


class Dictionary:
    def __init__(self, data: dict):
        self.fs_model = DataModel(data)

    def check_path(self, path):
        parts = str(path).split(os.sep)
        d = self.fs_model.dat
        try:
            for i in parts:
                d = d[i]
        except (KeyError, TypeError):
            raise FileNotFoundError
        return path

    def get_devices(self):
        for i in self.fs_model.dat:
            yield i, i, None

    def get_icon(self, path):
        return QtGui.QIcon()

    def get_places(self):
        raise NotImplementedError

    def init_completer(self, edit_widget):
        "Init QCompleter to work with filesystem"
        completer = QtWidgets.QCompleter(edit_widget)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(self.fs_model)
        # Optimize performance https://stackoverflow.com/a/33454284/1119602
        popup = completer.popup()
        popup.setUniformItemSizes(True)
        popup.setLayoutMode(QtWidgets.QListView.Batched)
        edit_widget.setCompleter(completer)
        edit_widget.textEdited.connect(self.fs_model.setPathPrefix)
        return completer


class DataModel(QtCore.QStringListModel):
    def __init__(self, data: dict):
        super().__init__()
        self.current_path: "Path|None" = None
        self.dat = data

    def data(self, index, role):
        "Get names/icons of files"
        default = super().data(index, role)
        if role == Qt.DisplayRole:
            return Path(default).name
        return default

    def setPathPrefix(self, prefix: str):
        path = Path(prefix)
        if not prefix.endswith(os.path.sep):
            path = path.parent
        if path == self.current_path:
            return  # already listed
        d: dict = self.dat
        for i in path.parts:
            d = d[str(i)]
        self.setStringList((str(path / k) for k in (d.keys() if d else ())))
        self.current_path = path
