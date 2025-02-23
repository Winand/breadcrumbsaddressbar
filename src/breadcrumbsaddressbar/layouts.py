from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt

class LeftHBoxLayout(QtWidgets.QHBoxLayout):
    '''
    Left aligned horizontal layout.
    Hides items similar to Windows Explorer address bar.
    '''
    # Signal is emitted when an item is hidden/shown or removed with `takeAt`
    widget_state_changed = QtCore.Signal(object, bool)

    def __init__(self, parent=None, minimal_space=0.1):
        super().__init__(parent)
        self.first_visible = 0
        self.set_space_widget()
        self.set_minimal_space(minimal_space)

    def set_space_widget(self, widget=None, stretch=1):
        """
        Set widget to be used to fill empty space to the right
        If `widget`=None the stretch item is used (by default)
        """
        super().takeAt(self.count())
        if widget:
            super().addWidget(widget, stretch)
        else:
            self.addStretch(stretch)

    def space_widget(self):
        "Widget used to fill free space"
        return self[self.count()]

    def setGeometry(self, rc:QtCore.QRect):
        "`rc` - layout's rectangle w/o margins"
        super().setGeometry(rc)  # perform the layout
        min_sp = self.minimal_space()
        if min_sp < 1:  # percent
            min_sp *= rc.width()
        free_space = self[self.count()].geometry().width() - min_sp
        if free_space < 0 and self.count_visible() > 1:  # hide more items
            widget = self[self.first_visible].widget()
            widget.hide()
            self.first_visible += 1
            self.widget_state_changed.emit(widget, False)
        elif free_space > 0 and self.count_hidden():  # show more items
            widget = self[self.first_visible-1].widget()
            w_width = widget.width() + self.spacing()
            if w_width <= free_space:  # enough space to show next item
                # setGeometry is called after show
                QtCore.QTimer.singleShot(0, widget.show)
                self.first_visible -= 1
                self.widget_state_changed.emit(widget, True)

    def count_visible(self):
        "Count of visible widgets"
        return self.count(visible=True)

    def count_hidden(self):
        "Count of hidden widgets"
        return self.count(visible=False)

    def minimumSize(self):
        margins = self.contentsMargins()
        return QtCore.QSize(margins.left() + margins.right(),
                            margins.top() + 24 + margins.bottom())

    def addWidget(self, widget, stretch=0, alignment=None):
        "Append widget to layout, make its width fixed"
        # widget.setMinimumSize(widget.minimumSizeHint())  # FIXME:
        super().insertWidget(self.count(), widget, stretch,
                             alignment or Qt.Alignment(0))

    def count(self, visible=None):
        "Count of items in layout: `visible`=True|False(hidden)|None(all)"
        cnt = super().count() - 1  # w/o last stretchable item
        if visible is None:  # all items
            return cnt
        if visible:  # visible items
            return cnt - self.first_visible
        return self.first_visible  # hidden items

    def widgets(self, state='all'):
        "Iterate over child widgets"
        for i in range(self.first_visible if state=='visible' else 0,
                       self.first_visible if state=='hidden' else self.count()
                       ):
            yield self[i].widget()

    def set_minimal_space(self, value):
        """
        Set minimal size of space area to the right:
        [0.0, 1.0) - % of the full width
        [1, ...) - size in pixels
        """
        self._minimal_space = value
        self.invalidate()

    def minimal_space(self):
        "See `set_minimal_space`"
        return self._minimal_space

    def __getitem__(self, index):
        "`itemAt` slices wrapper"
        if index < 0:
            index = self.count() + index
        return self.itemAt(index)

    def takeAt(self, index):
        "Return an item at the specified `index` and remove it from layout"
        if index < self.first_visible:
            self.first_visible -= 1
        item = super().takeAt(index)
        self.widget_state_changed.emit(item.widget(), False)
        return item
