"""
Dictionary data provider uses dict as source of data.

Keys are names of nodes, values are children of nodes. All keys are converted to
strings on load. Each node may include special metadata child in one of the following forms:
* Full - "/metadata" key with a dict of values:
    "nodename": {
        "/metadata": {
            "icon": "DirIcon",  # default icon for all items
        }, ...
    }
* Short - "/metadata" key with a string of comma-separated key=value pairs:
    "nodename": {
        "/metadata": "icon=FileIcon", ...
    }
* Compact - string of comma-separated key=value pairs. This form can be used
  if there're no other children in the node:
    "nodename": "icon=FileIcon"

Metadata on the root level is applied to all nodes.
Supported metadata:
* "icon": node icon which is a name of Qt StandardIcon without SP_ prefix.
          If not specified, DirIcon is used (default)

Example:
{
    "root1": {
        "dir1": "icon=FileIcon",
        "dir2": None,
    },
    "root2": {
        "dir1": None,
        "dir2": {
            "/metadata": "icon=FileIcon",
        },
    },
    "/metadata": {
        "icon": "DirIcon",  # default icon for all items
    }
}
"""

import os
from pathlib import Path

from breadcrumbsaddressbar.backend.interface import DataModel as _DataModel
from breadcrumbsaddressbar.backend.interface import DataProvider
from qtpy import QtCore, QtWidgets, QtGui
Qt = QtCore.Qt

cwd_path = Path()  # working dir (.) https://stackoverflow.com/q/51330297


class Dictionary(DataProvider):
    """
    Dictionary data provider
    """
    def __init__(self, data: dict):
        self.model = DataModel(data)

    def check_path(self, path: Path):
        "Checks that path exists in dictionary"
        if path == cwd_path:  # return first element of dict for cwd path
            return Path(next(iter(self.model.dat)))
        self.model._traverse(path)
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
    def_icon = "SP_FileIcon"  # if default icon is not specified in data
    icon_cache = {}

    def __init__(self, data: "dict[str, dict|str|None]"):
        super().__init__()
        self.current_path: "Path|None" = None
        self.dat = self._stringify_keys(data)  # copies nested dicts
        self._expand_metadata(self.dat)
        self.def_icon = self.metadata.get("icon", self.def_icon)

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

    def _expand_metadata(self, data: "dict[str, dict|str|None]"):
        "Expand string metadata to dict"
        for i in data:
            data_i = data[i]
            if isinstance(data_i, str):
                tmp_d = {}
                for kv in data_i.split(","):
                    k, v = kv.split("=")
                    tmp_d[k] = v
                data[i] = tmp_d if i == self.META else {self.META: tmp_d}
            elif i != self.META and isinstance(data_i, dict):
                self._expand_metadata(data_i)

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
            if icon_id.startswith("SP_"):
                self.icon_cache[icon_id] = QtWidgets.QApplication.instance().style() \
                    .standardIcon(getattr(QtWidgets.QStyle, icon_id))
            else:
                self.icon_cache[icon_id] = QtGui.QIcon(icon_id)
        return self.icon_cache[icon_id]

    def setPathPrefix(self, prefix: str):
        path = Path(prefix)
        if not prefix.endswith(os.path.sep):
            path = path.parent
        if path == self.current_path:
            return  # already listed
        d = self._traverse(path)
        # DataModel is a QStringListModel
        self.setStringList((str(path / k) for k in (d.keys() if d else ()) if k != self.META))
        self.current_path = path

    def _traverse(self, path: Path) -> "dict[str, dict]|None":
        "Traverse dictionary and return child items of path"
        dic = self.dat
        try:
            for i in path.parts:
                dic = dic[i]  # type: ignore
        except (KeyError, TypeError):
            raise FileNotFoundError
        return dic

    @property
    def metadata(self) -> dict:
        "Returns model's metadata as dict if any"
        return self.dat.get(self.META) or {}
