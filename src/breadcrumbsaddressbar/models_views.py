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
    `icon_provider` (func, 'internal', None) - a function which gets path
                                               and returns QIcon
    """
    def __init__(self, filter_=None, fs_engine='qt', icon_provider='internal'):
        super().__init__()
        self.current_path = None
        self.fs_engine = fs_engine
        self.filter = filter_
        if icon_provider == 'internal':
            self.icons = QtWidgets.QFileIconProvider()
            self.icon_provider = self.get_icon
        else:
            self.icon_provider = icon_provider

    def data(self, index, role):
        "Get names/icons of files"
        default = super().data(index, role)
        if role == Qt.DecorationRole and self.icon_provider:
            # self.setData(index, dat, role)
            return self.icon_provider(super().data(index, Qt.DisplayRole))
        if role == Qt.DisplayRole:
            return Path(default).name
        return default

    def get_icon(self, path):
        "Internal icon provider"
        return self.icons.icon(QtCore.QFileInfo(path))

    def get_file_list(self, path):
        "List entries in `path` directory"
        lst = None
        if self.fs_engine == 'pathlib':
            lst = self.sort_paths([i for i in path.iterdir()
                                   if self.filter != 'dirs' or i.is_dir()])
        elif self.fs_engine == 'qt':
            qdir = QtCore.QDir(str(path))
            qdir.setFilter(qdir.Filter.NoDotAndDotDot | qdir.Filter.Hidden |
                (qdir.Filter.Dirs if self.filter == 'dirs' else qdir.Filter.AllEntries))
            names = qdir.entryList(sort=QtCore.QDir.SortFlag.DirsFirst |
                                   QtCore.QDir.SortFlag.LocaleAware)
            lst = [str(path / i) for i in names]
        return lst

    @staticmethod
    def sort_paths(paths):
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


class MenuListView(QtWidgets.QMenu):
    """
    QMenu with QListView.
    Supports `activated`, `clicked`, `setModel`.
    """
    max_visible_items = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listview = lv = QtWidgets.QListView()
        lv.setFrameShape(lv.Shape.NoFrame)
        lv.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        pal = lv.palette()
        pal.setColor(pal.ColorRole.Base, self.palette().color(pal.ColorRole.Window))
        lv.setPalette(pal)

        act_wgt = QtWidgets.QWidgetAction(self)
        act_wgt.setDefaultWidget(lv)
        self.addAction(act_wgt)

        self.activated = lv.activated
        self.clicked = lv.clicked
        self.setModel = lv.setModel

        lv.sizeHint = self.size_hint
        lv.minimumSizeHint = self.size_hint
        lv.mousePressEvent = self.mouse_press_event
        lv.mouseMoveEvent = self.update_current_index
        lv.setMouseTracking(True)  # receive mouse move events
        lv.leaveEvent = self.clear_selection
        lv.mouseReleaseEvent = self.mouse_release_event
        lv.keyPressEvent = self.key_press_event
        lv.setFocusPolicy(Qt.NoFocus)  # no focus rect
        lv.setFocus()

        self.last_index = QtCore.QModelIndex()  # selected index
        self.flag_mouse_l_pressed = False

    def key_press_event(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.last_index.isValid():
                self.activated.emit(self.last_index)
            self.close()
        elif key == Qt.Key_Escape:
            self.close()
        elif key in (Qt.Key_Down, Qt.Key_Up):
            model = self.listview.model()
            row_from, row_to = 0, model.rowCount()-1
            if key == Qt.Key_Down:
                row_from, row_to = row_to, row_from
            if self.last_index.row() in (-1, row_from):  # no index=-1
                index = model.index(row_to, 0)
            else:
                shift = 1 if key == Qt.Key_Down else -1
                index = model.index(self.last_index.row()+shift, 0)
            self.listview.setCurrentIndex(index)
            self.last_index = index

    def update_current_index(self, event):
        self.last_index = self.listview.indexAt(event.pos())
        self.listview.setCurrentIndex(self.last_index)

    def clear_selection(self, event=None):
        self.listview.clearSelection()
        # selectionModel().clear() leaves selected item in Fusion theme
        self.listview.setCurrentIndex(QtCore.QModelIndex())
        self.last_index = QtCore.QModelIndex()
    
    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self.flag_mouse_l_pressed = True
            self.update_current_index(event)

    def mouse_release_event(self, event):
        """
        When item is clicked w/ left mouse button close menu, emit `clicked`.
        Check if there was left button press event inside this widget.
        """
        if event.button() == Qt.LeftButton and self.flag_mouse_l_pressed:
            self.flag_mouse_l_pressed = False
            if self.last_index.isValid():
                self.clicked.emit(self.last_index)
            self.close()

    def size_hint(self):
        lv = self.listview
        width = lv.sizeHintForColumn(0)
        width += lv.verticalScrollBar().sizeHint().width()
        if isinstance(self.parent(), QtWidgets.QToolButton):
            width = max(width, self.parent().width())
        visible_rows = min(self.max_visible_items, lv.model().rowCount())
        return QtCore.QSize(width, visible_rows * lv.sizeHintForRow(0))
