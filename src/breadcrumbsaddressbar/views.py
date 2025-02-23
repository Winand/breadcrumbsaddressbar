from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt


class MenuListView(QtWidgets.QMenu):
    """
    QMenu with QListView.
    Supports `activated`, `clicked`, `setModel`.
    """
    max_visible_items = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listview = lv = QtWidgets.QListView()
        lv.setFrameShape(lv.NoFrame)
        lv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pal = lv.palette()
        pal.setColor(pal.Base, self.palette().color(pal.Window))
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
