import os
import platform
from pathlib import Path
from typing import Union as U, Final

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

from .interface import DataProvider
from .models import FilenameModel
from ..platform.common import if_platform

if platform.system() == "Windows":
    from ..platform.windows import get_path_label, read_link

TRANSP_ICON_SIZE: Final = 40, 40  # px, size of generated semi-transparent icons


class Filesystem(DataProvider):
    """
    Local filesystem provider
    """
    def __init__(self):
        self.file_ico_prov = QtWidgets.QFileIconProvider()
        # Custom icons cause a performance impact https://doc.qt.io/qt-5/qfileiconprovider.html#Option-enum
        # self.file_ico_prov.setOptions(self.file_ico_prov.DontUseCustomDirectoryIcons)
        self.model = FilenameModel('dirs', icon_provider=self.get_icon)
        self.os_type = platform.system()

    def check_path(self, path: Path):
        """
        Returns resolved path or raises FileNotFoundError if path is not valid
        """
        # C: -> C:\, folder\..\folder -> folder
        path = path.resolve()  # may raise PermissionError
        if not path.exists():
            raise FileNotFoundError
        return path

    def get_devices(self):
        """
        Return devices and network locations (if any)
        """
        for i in QtCore.QStorageInfo.mountedVolumes():  # QDir.drives():
            path, label = i.rootPath(), i.displayName()
            if label == path and self.os_type == "Windows":
                label = self._get_path_label(path)
            elif self.os_type == "Linux" and not path.startswith("/media"):
                # Add to list only volumes in /media
                continue
            caption = "%s (%s)" % (label, path.rstrip(r"\/"))
            icon = self.get_icon(path)
            yield caption, path, icon
        try:  # Network locations
            for label, path, icon in self._list_network_locations():
                yield label, path, icon
        except NotImplementedError:
            pass

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

    def _get_path_label(self, drive_path):
        "Try to get path label using Shell32 on Windows"
        return get_path_label(drive_path.replace("/", "\\"))

    def get_places(self):
        """
        Return known places list ((name, path), ...)
        """
        QSP = QtCore.QStandardPaths
        uname = os.environ.get('USER') or os.environ.get('USERNAME') or "Home"
        for name, path in (
                ("Desktop", QSP.writableLocation(QSP.DesktopLocation)),
                (uname, QSP.writableLocation(QSP.HomeLocation)),
                ("Documents", QSP.writableLocation(QSP.DocumentsLocation)),
                ("Downloads", QSP.writableLocation(QSP.DownloadLocation)),
                ):
            if self.os_type == "Windows":
                name = self._get_path_label(path)
            yield name, path

    def init_completer(self, edit_widget: QtWidgets.QWidget):
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

    @if_platform('Windows')
    def _list_network_locations(self):
        "List (name, path) locations in Network Shortcuts folder on Windows"
        HOME = QtCore.QStandardPaths.HomeLocation
        user_folder = QtCore.QStandardPaths.writableLocation(HOME)
        network_shortcuts = user_folder + "/AppData/Roaming/Microsoft/Windows/Network Shortcuts"
        for i in Path(network_shortcuts).iterdir():
            if not i.is_dir():
                continue
            link = Path(i) / "target.lnk"
            if not link.exists():
                continue
            # path = QtCore.QFileInfo(str(link)).symLinkTarget()
            path = read_link(link)
            if not path:
                # By default `read_link` reads only filesystem paths and fails for e.g. FTP
                # QFileInfo.symLinkTarget also fails with FTP links
                continue
            # Get icon for target.lnk parent folder, because it's faster than
            # reading icon for link target location or link file itself
            # if network location is unavailable. A drawback is that
            # QFileIconProvider returns icon with a shortcut arrow then.
            icon = self.get_icon(link.parent)
            yield i.name, path, icon
