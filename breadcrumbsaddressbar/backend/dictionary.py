import os
from pathlib import Path

from breadcrumbsaddressbar.backend.interface import DataModel as _DataModel
from breadcrumbsaddressbar.backend.interface import DataProvider
from qtpy import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt



class Dictionary(DataProvider):
    """
    Dictionary data provider
    """
    def __init__(self, data: dict):
        self.model = DataModel(data)

    def check_path(self, path: Path):
        "Checks that path exists in dictionary"
        d = self.model.dat
        try:
            for i in path.parts:
                d = d[i]
        except (KeyError, TypeError):
            raise FileNotFoundError
        return path

    def get_devices(self):
        "Top-level items in dictionary"
        for i in self.model.dat:
            if i != self.model.META:
                yield i, i, None

    def init_completer(self, edit_widget):
        "Init QCompleter to work with filesystem"
        completer = QtWidgets.QCompleter(edit_widget)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(self.model)
        # Optimize performance https://stackoverflow.com/a/33454284/1119602
        popup = completer.popup()
        popup.setUniformItemSizes(True)
        popup.setLayoutMode(QtWidgets.QListView.Batched)
        edit_widget.setCompleter(completer)
        edit_widget.textEdited.connect(self.model.setPathPrefix)
        return completer


class DataModel(_DataModel):
    "Data model for Dictionary provider"
    META = "/metadata"
    def_icon = "DirIcon"  # if default icon is not specified in data
    icon_cache = {}

    def __init__(self, data: "dict[str, dict|str|None]"):
        super().__init__()
        self.current_path: "Path|None" = None
        self.dat = self._stringify_keys(data)  # copies nested dicts
        self.def_icon = (self.dat.get(self.META) or {}).get("icon", self.def_icon)

    def _stringify_keys(self, data: "dict[str, dict|str|None]"):
        "Stringify keys of dictionary"
        # see also https://stackoverflow.com/questions/62198378/numeric-keys-in-yaml-files
        # https://stackoverflow.com/questions/47568356/python-convert-all-keys-to-strings
        new_d = {}
        for i in data:
            data_i = data[i]
            new_d[str(i)] = self._stringify_keys(data_i) \
                            if isinstance(data_i, dict) \
                            else data_i
        return new_d
    def data(self, index, role):
        "Get names/icons of files"
        default = super().data(index, role)
        if role == Qt.DecorationRole:
            return self.get_icon(
                super().data(index, Qt.DisplayRole)
            )
        if role == Qt.DisplayRole:
            return Path(default).name
        return default

    def get_icon(self, path: Path):
        "Returns folder icon"
        icon_id = self.def_icon
        node = self._traverse(Path(path))
        if node:
            node = node.get(self.META)
            if node:
                icon_id = node.get("icon", icon_id)
        if icon_id not in self.icon_cache:
            self.icon_cache[icon_id] = QtWidgets.QApplication.instance().style() \
                .standardIcon(getattr(QtWidgets.QStyle, "SP_" + icon_id))
        return self.icon_cache[icon_id]

    def setPathPrefix(self, prefix: str):
        path = Path(prefix)
        if not prefix.endswith(os.path.sep):
            path = path.parent
        if path == self.current_path:
            return  # already listed
        d: dict = self.dat
        for i in path.parts:
            d = d[str(i)]
        # DataModel is a QStringListModel
        self.setStringList((str(path / k) for k in (d.keys() if d else ()) if k != self.META))
        self.current_path = path
