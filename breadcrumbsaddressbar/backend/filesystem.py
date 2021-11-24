import platform
from pathlib import Path
from typing import Union as U

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

from ..models_views import FilenameModel
from ..platform.common import if_platform

if platform.system() == "Windows":
    from ..platform.windows import read_link

TRANSP_ICON_SIZE = 40, 40  # px, size of generated semi-transparent icons


class Filesystem:
    def __init__(self):
        self.file_ico_prov = QtWidgets.QFileIconProvider()
        # Custom icons cause a performance impact https://doc.qt.io/qt-5/qfileiconprovider.html#Option-enum
        # self.file_ico_prov.setOptions(self.file_ico_prov.DontUseCustomDirectoryIcons)
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

    @if_platform('Windows')
    def list_network_locations(self):
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
