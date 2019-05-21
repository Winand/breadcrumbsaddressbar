import os.path
from pathlib import Path
from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt

class FilenameModel(QtCore.QStringListModel):
    """
    Model used by QCompleter for file name completions.
    Constructor options:
    `filter_` (None, 'dirs') - include all entries or folders only
    `fs_engine` ('qt', 'pathlib') - enumerate files using `QDir` or `pathlib`
    """
    def __init__(self, filter_=None, fs_engine='qt'):
        super().__init__()
        self.icons = QtWidgets.QFileIconProvider()
        self.current_path = None
        self.fs_engine = fs_engine
        self.filter = filter_

    def data(self, index, role):
        "Get names/icons of files"
        default = super().data(index, role)
        if role == Qt.DecorationRole:
            fileinfo = QtCore.QFileInfo(super().data(index, Qt.DisplayRole))
            dat = self.icons.icon(fileinfo)
            # self.setData(index, dat, role)
            return dat
        if role == Qt.DisplayRole:
            return Path(default).name
        return default

    def get_file_list(self, path):
        "List entries in `path` directory"
        lst = None
        if self.fs_engine == 'pathlib':
            lst = self.sort_paths([i for i in path.iterdir()
                                   if self.filter != 'dirs' or i.is_dir()])
        elif self.fs_engine == 'qt':
            qdir = QtCore.QDir(str(path))
            qdir.setFilter(qdir.NoDotAndDotDot | qdir.Hidden |
                (qdir.Dirs if self.filter == 'dirs' else qdir.AllEntries))
            names = qdir.entryList(sort=QtCore.QDir.DirsFirst |
                                   QtCore.QDir.LocaleAware)
            lst = [str(path / i) for i in names]
        return lst

    def sort_paths(self, paths):
        "Windows-Explorer-like filename sorting (for 'pathlib' engine)"
        dirs, files = [], []
        for i in paths:
            if i.is_dir():
                dirs.append(str(i))
            else:
                files.append(str(i))
        return sorted(dirs, key=str.lower) + sorted(files, key=str.lower)

    def setPathPrefix(self, prefix):
        path = Path(prefix)
        if not prefix.endswith(os.path.sep):
            path = path.parent
        if path == self.current_path:
            return  # already listed
        if not path.exists():
            return  # wrong path
        self.setStringList(self.get_file_list(path))
        self.current_path = path
