from pathlib import Path
from typing import Union as U

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

from ..models_views import FilenameModel

TRANSP_ICON_SIZE = 40, 40  # px, size of generated semi-transparent icons


class Filesystem:
    def __init__(self):
        self.file_ico_prov = QtWidgets.QFileIconProvider()
        self.fs_model = FilenameModel('dirs', icon_provider=self.get_icon)

    def check_path(self, path: Path):
        # C: -> C:\, folder\..\folder -> folder
        path = path.resolve()  # may raise PermissionError
        if not path.exists():
            raise FileNotFoundError
        return path

    def get_icon(self, path: U[str, Path]):
        "Path -> QIcon"
        fileinfo = QtCore.QFileInfo(str(path))
        dat = self.file_ico_prov.icon(fileinfo)
        if fileinfo.isHidden():
            pmap = QtGui.QPixmap(*TRANSP_ICON_SIZE)
            pmap.fill(Qt.transparent)
            painter = QtGui.QPainter(pmap)
            painter.setOpacity(0.5)
            dat.paint(painter, 0, 0, *TRANSP_ICON_SIZE)
            painter.end()
            dat = QtGui.QIcon(pmap)
        return dat

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
