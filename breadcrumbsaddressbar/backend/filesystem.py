from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

TRANSP_ICON_SIZE = 40, 40  # px, size of generated semi-transparent icons


class Filesystem:
    def __init__(self):
        self.file_ico_prov = QtWidgets.QFileIconProvider()

    def check_path(self, path: Path):
        # C: -> C:\, folder\..\folder -> folder
        path = path.resolve()  # may raise PermissionError
        if not path.exists():
            raise FileNotFoundError
        return path

    def get_icon(self, path: Path):
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
