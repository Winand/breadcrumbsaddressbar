import os

from qtpy import QtCore, QtGui


class Dictionary:
    def __init__(self, data):
        self.data = data
        self.fs_model = QtCore.QStringListModel()
        self.fs_model.setPathPrefix = lambda _: None

    def check_path(self, path):
        parts = str(path).split(os.sep)
        d = self.data
        try:
            for i in parts:
                d = d[i]
        except (KeyError, TypeError):
            raise FileNotFoundError
        return path

    def get_devices(self):
        for i in self.data:
            yield i, i, None

    def get_icon(self, path):
        return QtGui.QIcon()

    def get_places(self):
        raise NotImplementedError

    def init_completer(self, edit_widget):
        raise NotImplementedError
