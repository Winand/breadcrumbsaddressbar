"""
Qt navigation bar with breadcrumbs
Andrey Makarov, 2019
"""

from pathlib import Path
import os
from qtpy import QtWidgets, QtGui, QtCore
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

class BreadcrumbsAddressBar(QtWidgets.QFrame):
    "Windows Explorer-like address bar"
    listdir_error = QtCore.Signal(Path)  # failed to list a directory
    path_error = QtCore.Signal(Path)  # entered path does not exist
    path_selected = QtCore.Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)

        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background,
                     pal.color(QtGui.QPalette.Base))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setFrameShape(self.StyledPanel)
        self.layout().setContentsMargins(4, 0, 0, 0)
        self.layout().setSpacing(0)

        # Edit presented path textually
        self.line_address = QtWidgets.QLineEdit(self)
        self.line_address.setFrame(False)
        self.line_address.hide()
        self.line_address.keyPressEvent_super = self.line_address.keyPressEvent
        self.line_address.keyPressEvent = self.line_address_keyPressEvent
        self.line_address.focusOutEvent = self.line_address_focusOutEvent
        self.line_address.contextMenuEvent_super = self.line_address.contextMenuEvent
        self.line_address.contextMenuEvent = self.line_address_contextMenuEvent
        # self.line_address.textEdited.connect(self.line_address_textEdited)
        self.completer = QtWidgets.QCompleter(self)  # FIXME:
        fs_model = QtWidgets.QFileSystemModel(self.completer)
        # fs_model.directoryLoaded.connect(self.completer.complete)  # QTBUG-38014
        fs_model.setRootPath("")  # "//mybooklive"
        fs_model.setFilter(QtCore.QDir.Dirs|QtCore.QDir.Drives|
                           QtCore.QDir.NoDotAndDotDot|QtCore.QDir.AllDirs)
        self.completer.setModel(fs_model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)  # FIXME: ???
        self.completer.activated.connect(self.set_path)
        self.line_address.setCompleter(self.completer)
        layout.addWidget(self.line_address)

        # Container for `btn_crumbs_hidden`, `crumbs_panel`, `switch_space`
        self.crumbs_container = QtWidgets.QWidget(self)
        crumbs_cont_layout = QtWidgets.QHBoxLayout(self.crumbs_container)
        crumbs_cont_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_cont_layout.setSpacing(0)
        layout.addWidget(self.crumbs_container)

        # Hidden breadcrumbs menu button
        self.btn_crumbs_hidden = QtWidgets.QToolButton(self)
        self.btn_crumbs_hidden.setAutoRaise(True)
        self.btn_crumbs_hidden.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_crumbs_hidden.setArrowType(Qt.LeftArrow)
        self.btn_crumbs_hidden.setStyleSheet("QToolButton::menu-indicator {"
                                             "image: none;}")
        self.btn_crumbs_hidden.setMinimumSize(self.btn_crumbs_hidden.minimumSizeHint())
        self.btn_crumbs_hidden.hide()
        crumbs_cont_layout.addWidget(self.btn_crumbs_hidden)
        menu = QtWidgets.QMenu(self.btn_crumbs_hidden)  # FIXME:
        menu.aboutToShow.connect(self._hidden_crumbs_menu_show)
        self.btn_crumbs_hidden.setMenu(menu)

        # Container for breadcrumbs
        self.crumbs_panel = QtWidgets.QWidget(self)
        crumbs_layout = LeftHBoxLayout(self.crumbs_panel)
        crumbs_layout.widget_state_changed.connect(self.crumb_hide_show)
        crumbs_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_layout.setSpacing(0)
        crumbs_cont_layout.addWidget(self.crumbs_panel)

        # Clicking on empty space to the right puts the bar into edit mode
        self.switch_space = QtWidgets.QWidget(self)
        # s_policy = self.switch_space.sizePolicy()
        # s_policy.setHorizontalStretch(1)
        # self.switch_space.setSizePolicy(s_policy)
        self.switch_space.mouseReleaseEvent = self.switch_space_mouse_up
        # crumbs_cont_layout.addWidget(self.switch_space)
        crumbs_layout.set_space_widget(self.switch_space)

        self.btn_browse = QtWidgets.QToolButton(self)
        self.btn_browse.setAutoRaise(True)
        self.btn_browse.setText("...")
        self.btn_browse.setToolTip("Browse for folder")
        self.btn_browse.clicked.connect(self._browse_for_folder)
        layout.addWidget(self.btn_browse)

        self.setMaximumHeight(self.line_address.height())  # FIXME:

        # self.l_breadcrumbs = None
        self.ignore_resize = False
        self.path_ = None
        self.set_path(Path())

    def line_address_contextMenuEvent(self, event):
        self.line_address_context_menu_flag = True
        self.line_address.contextMenuEvent_super(event)

    def line_address_focusOutEvent(self, event):
        if getattr(self, 'line_address_context_menu_flag', False):
            self.line_address_context_menu_flag = False
            return  # do not cancel edit on context menu
        self._cancel_edit()

    def _hidden_crumbs_menu_show(self):
        "SLOT: fill menu with hidden breadcrumbs list"
        menu = self.sender()
        menu.clear()
        # hid_count = self.crumbs_panel.layout().count_hidden()
        # for i in self.l_breadcrumbs[hid_count-1::-1]:
        for i in reversed(list(self.crumbs_panel.layout().widgets('hidden'))):
            action = menu.addAction(i.text())
            action.path = i.path
            action.triggered.connect(self.set_path)

    def _browse_for_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose folder", str(self.path()))
        if path:
            self.set_path(path)

    def line_address_keyPressEvent(self, event):
        "Actions to take after a key press in text address field"
        if event.key() == Qt.Key_Escape:
            self._cancel_edit()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.set_path(self.line_address.text())
            self._show_address_field(False)
        # elif event.text() == os.path.sep:  # FIXME: separator cannot be pasted
        #     print('fill completer data here')
        #     paths = [str(i) for i in
        #              Path(self.line_address.text()).iterdir() if i.is_dir()]
        #     self.completer.model().setStringList(paths)
        self.line_address.keyPressEvent_super(event)

    def _clear_crumbs(self):
        layout = self.crumbs_panel.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # self.l_crumbs_hidden, self.l_crumbs_visible = [], []  # init
        # self.l_breadcrumbs = []

    def _insert_crumb(self, path):
        btn = QtWidgets.QToolButton(self.crumbs_panel)
        btn.setAutoRaise(True)
        btn.setPopupMode(btn.MenuButtonPopup)
        # FIXME: C:\ has no name. Use rstrip on Windows only?
        crumb_text = path.name or str(path).upper().rstrip(os.path.sep)
        btn.setText(crumb_text)
        btn.path = path
        btn.clicked.connect(self.crumb_clicked)
        menu = QtWidgets.QMenu(btn)
        menu.aboutToShow.connect(self.crumb_menu_show)
        menu.aboutToHide.connect(self.crumb_menu_hide)
        # scrollable menu https://stackoverflow.com/a/14719633/1119602
        menu.setStyleSheet("QMenu { menu-scrollable: 1; }")
        btn.setMenu(menu)
        self.crumbs_panel.layout().insertWidget(0, btn)
        btn.setMinimumSize(btn.minimumSizeHint())  # fixed size breadcrumbs
        # print(self._check_space_width(btn.minimumWidth()))
        # print(btn.size(), btn.sizeHint(), btn.minimumSizeHint())
        # self.l_crumbs_visible.insert(0, btn)
        # self.l_breadcrumbs.insert(0, btn)

    def crumb_clicked(self):
        "SLOT: breadcrumb was clicked"
        self.set_path(self.sender().path)

    def crumb_menu_show(self):
        "SLOT: fill subdirectory list on menu open"
        menu = self.sender()
        context_root = menu.parent().path
        try:
            for i in context_root.iterdir():
                if not i.is_dir():
                    continue
                action = menu.addAction(i.name)
                action.path = i
                action.triggered.connect(self.set_path)
        except PermissionError:
            self.listdir_error.emit(context_root)

    def crumb_menu_hide(self):
        "SLOT: Clear sub-dir menu on hide but let action trigger first"
        QtCore.QTimer.singleShot(0, self.sender().clear)

    def set_path(self, path=None):
        """
        Set path displayed in this BreadcrumbsAddressBar
        Returns `False` if path does not exist or permission error.
        Can be used as a SLOT: `sender().path` is used if `path` is `None`)
        """
        path, emit_err = Path(path or self.sender().path), None
        try:  # C: -> C:\, folder\..\folder -> folder
            path = path.resolve()
        except PermissionError:
            emit_err = self.listdir_error
        if not path.exists():
            emit_err = self.path_error
        self._cancel_edit()  # exit edit mode
        if emit_err:  # permission error or path does not exist
            emit_err.emit(path)
            return False
        self._clear_crumbs()
        self.path_ = path
        self.line_address.setText(str(path))
        self._insert_crumb(path)
        while path.parent != path:
            path = path.parent
            self._insert_crumb(path)
        # self.l_crumbs_visible[-1].setMinimumSize(0, 0)  # FIXME: last piece is resizable?
        # QtCore.QTimer.singleShot(0, self._show_hide_breadcrumbs)
        self.path_selected.emit(path)
        return True

    def _cancel_edit(self):
        "Set edit line text back to current path and switch to view mode"
        self.line_address.setText(str(self.path()))  # revert path
        self._show_address_field(False)  # switch back to breadcrumbs view

    def path(self):
        "Get path displayed in this BreadcrumbsAddressBar"
        return self.path_

    def switch_space_mouse_up(self, event):
        "EVENT: switch_space mouse clicked"
        if event.button() != Qt.LeftButton:  # left click only
            return
        self._show_address_field(True)

    def _show_address_field(self, b_show):
        "Show text address field"
        if b_show:
            self.crumbs_container.hide()
            self.line_address.show()
            self.line_address.setFocus()
            self.line_address.selectAll()
        else:
            self.line_address.hide()
            self.crumbs_container.show()

    def crumb_hide_show(self, widget, state:bool):
        "SLOT: a breadcrumb is hidden/removed or shown"
        layout = self.crumbs_panel.layout()
        if layout.count_hidden() > 0:
            self.btn_crumbs_hidden.show()
        else:
            self.btn_crumbs_hidden.hide()

    def minimumSizeHint(self):
        # print(self.layout().minimumSize().width())
        return QtCore.QSize(150, self.line_address.height())


if __name__ == '__main__':
    from qtapp import QtForm

    class Form(QtWidgets.QWidget):
        _layout_ = QtWidgets.QHBoxLayout
        _loop_ = True

        def perm_err(self, path):
            print('perm err', path)

        def path_err(self, path):
            print('path err', path)
        
        def b_clicked(self):
            pass
            # print(self.address._check_space_width())
            # print([i.width() for i in self.address.l_crumbs_visible])  
            # print([i.minimumSizeHint() for i in self.address.l_crumbs_visible])  

        def __init__(self):  # pylint: disable=super-init-not-called
            self.address = BreadcrumbsAddressBar()
            self.b = QtWidgets.QPushButton("test_button_long_text", self)
            self.b.setFixedWidth(200)
            self.layout().addWidget(self.b)
            self.layout().addWidget(self.address)
            self.address.listdir_error.connect(self.perm_err)
            self.address.path_error.connect(self.path_err)
            # self.address.set_path(r"C:\Windows\System32\drivers\etc")
            # print(self.b.width())
            # self.b.hide()
            # QtCore.QTimer.singleShot(0, lambda: print(self.b.width()))
            def act():
                for i in self.address.crumbs_panel.layout().widgets('hidden'):
                    print(i.text())
            self.b.clicked.connect(act)

    QtForm(Form)
