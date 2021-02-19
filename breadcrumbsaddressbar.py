"""
Qt navigation bar with breadcrumbs
Andrey Makarov, 2019
"""

import platform
from pathlib import Path
import os
from typing import Union
from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt
if __package__:  # https://stackoverflow.com/a/28151907
    from .models_views import FilenameModel, MenuListView
    from .layouts import LeftHBoxLayout
    from .stylesheet import style_root_toolbutton
else:
    from models_views import FilenameModel, MenuListView
    from layouts import LeftHBoxLayout
    from stylesheet import style_root_toolbutton

TRANSP_ICON_SIZE = 40, 40  # px, size of generated semi-transparent icons


class BreadcrumbsAddressBar(QtWidgets.QFrame):
    "Windows Explorer-like address bar"
    listdir_error = QtCore.Signal(Path)  # failed to list a directory
    path_error = QtCore.Signal(Path)  # entered path does not exist
    path_selected = QtCore.Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.os_type = platform.system()

        self.style_crumbs = StyleProxy(
            QtWidgets.QStyleFactory.create(
                QtWidgets.QApplication.instance().style().objectName()
            ),
            QtGui.QPixmap("iconfinder_icon-ios7-arrow-right_211607.png")
        )

        layout = QtWidgets.QHBoxLayout(self)

        self.file_ico_prov = QtWidgets.QFileIconProvider()
        self.fs_model = FilenameModel('dirs', icon_provider=self.get_icon)

        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background,
                     pal.color(QtGui.QPalette.Base))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setFrameShape(self.StyledPanel)
        self.layout().setContentsMargins(4, 0, 0, 0)
        self.layout().setSpacing(0)

        self.path_icon = QtWidgets.QLabel(self)
        layout.addWidget(self.path_icon)

        # Edit presented path textually
        self.line_address = QtWidgets.QLineEdit(self)
        self.line_address.setFrame(False)
        self.line_address.hide()
        self.line_address.keyPressEvent = self.line_address_keyPressEvent
        self.line_address.focusOutEvent = self.line_address_focusOutEvent
        self.line_address.contextMenuEvent = self.line_address_contextMenuEvent
        layout.addWidget(self.line_address)
        # Add QCompleter to address line
        completer = self.init_completer(self.line_address, self.fs_model)
        completer.activated.connect(self.set_path)

        # Container for `btn_crumbs_hidden`, `crumbs_panel`, `switch_space`
        self.crumbs_container = QtWidgets.QWidget(self)
        crumbs_cont_layout = QtWidgets.QHBoxLayout(self.crumbs_container)
        crumbs_cont_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_cont_layout.setSpacing(0)
        layout.addWidget(self.crumbs_container)

        # Hidden breadcrumbs menu button
        self.btn_root_crumb = QtWidgets.QToolButton(self)
        self.btn_root_crumb.setAutoRaise(True)
        self.btn_root_crumb.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_root_crumb.setArrowType(Qt.RightArrow)
        self.btn_root_crumb.setStyleSheet(style_root_toolbutton)
        self.btn_root_crumb.setMinimumSize(self.btn_root_crumb.minimumSizeHint())
        crumbs_cont_layout.addWidget(self.btn_root_crumb)
        menu = QtWidgets.QMenu(self.btn_root_crumb)  # FIXME:
        menu.aboutToShow.connect(self._hidden_crumbs_menu_show)
        self.btn_root_crumb.setMenu(menu)
        self.init_rootmenu_places(menu)  # Desktop, Home, Downloads...
        self.update_rootmenu_devices()  # C:, D:...

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

        self.ignore_resize = False
        self.path_ = None
        self.set_path(Path())

    @staticmethod
    def init_completer(edit_widget, model):
        "Init QCompleter to work with filesystem"
        completer = QtWidgets.QCompleter(edit_widget)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(model)
        # Optimize performance https://stackoverflow.com/a/33454284/1119602
        popup = completer.popup()
        popup.setUniformItemSizes(True)
        popup.setLayoutMode(QtWidgets.QListView.Batched)
        edit_widget.setCompleter(completer)
        edit_widget.textEdited.connect(model.setPathPrefix)
        return completer

    def get_icon(self, path: Union[str, Path]):
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

    def line_address_contextMenuEvent(self, event):
        self.line_address_context_menu_flag = True
        QtWidgets.QLineEdit.contextMenuEvent(self.line_address, event)

    def line_address_focusOutEvent(self, event):
        if getattr(self, 'line_address_context_menu_flag', False):
            self.line_address_context_menu_flag = False
            return  # do not cancel edit on context menu
        self._cancel_edit()

    def _hidden_crumbs_menu_show(self):
        "SLOT: fill menu with hidden breadcrumbs list"
        menu = self.sender()
        if hasattr(self, 'actions_hidden_crumbs'):
            for action in self.actions_hidden_crumbs:
                menu.removeAction(action)
        self.actions_hidden_crumbs = []

        first_action = menu.actions()[0]  # places section separator
        for i in self.crumbs_panel.layout().widgets('hidden'):
            action = QtWidgets.QAction(self.get_icon(i.path), i.text(), menu)
            action.path = i.path
            action.triggered.connect(self.set_path)
            menu.insertAction(first_action, action)
            self.actions_hidden_crumbs.append(action)
            first_action = action

    def init_rootmenu_places(self, menu):
        "Init common places actions in menu"
        menu.addSeparator()
        QSP = QtCore.QStandardPaths
        uname = os.environ.get('USER') or os.environ.get('USERNAME') or "Home"
        for name, path in (
                ("Desktop", QSP.writableLocation(QSP.DesktopLocation)),
                (uname, QSP.writableLocation(QSP.HomeLocation)),
                ("Documents", QSP.writableLocation(QSP.DocumentsLocation)),
                ("Downloads", QSP.writableLocation(QSP.DownloadLocation)),
                ):
            action = menu.addAction(self.get_icon(path), name)
            action.path = path
            action.triggered.connect(self.set_path)

    def get_drive_label(self, drive_path):
        "Try to get drive label using Shell32"
        from platform_win import get_path_label
        return get_path_label(drive_path.replace("/", "\\"))

    @staticmethod
    def list_network_locations():
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
            path = QtCore.QFileInfo(str(link)).symLinkTarget()
            if path:  # `symLinkTarget` doesn't read e.g. FTP links
                yield i.name, path

    def update_rootmenu_devices(self):
        "Init or rebuild device actions in menu"
        menu = self.btn_root_crumb.menu()
        if hasattr(self, 'actions_devices'):
            for action in self.actions_devices:
                menu.removeAction(action)
        self.actions_devices = [menu.addSeparator()]
        for i in QtCore.QStorageInfo.mountedVolumes():  # QDir.drives():
            path, label = i.rootPath(), i.displayName()
            if label == path and self.os_type == "Windows":
                label = self.get_drive_label(path)
            caption = "%s (%s)" % (label, path.rstrip(r"\/"))
            action = menu.addAction(self.get_icon(path), caption)
            action.path = path
            action.triggered.connect(self.set_path)
            self.actions_devices.append(action)
        if self.os_type == "Windows":  # Network locations
            for label, path in self.list_network_locations():
                action = menu.addAction(self.get_icon(path), label)
                action.path = path
                action.triggered.connect(self.set_path)
                self.actions_devices.append(action)

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
        else:
            QtWidgets.QLineEdit.keyPressEvent(self.line_address, event)

    def _clear_crumbs(self):
        layout = self.crumbs_panel.layout()
        while layout.count():
            widget = layout.takeAt(0).widget()
            if widget:
                # Unset style or `StyleProxy.drawPrimitive` is called once with
                # mysterious `QWidget` instead of `QToolButton` (Windows 7)
                widget.setStyle(None)
                widget.deleteLater()

    def _insert_crumb(self, path):
        btn = QtWidgets.QToolButton(self.crumbs_panel)
        btn.setAutoRaise(True)
        btn.setPopupMode(btn.MenuButtonPopup)
        btn.setStyle(self.style_crumbs)
        btn.mouseMoveEvent = self.crumb_mouse_move
        btn.setMouseTracking(True)
        # FIXME: C:\ has no name. Use rstrip on Windows only?
        crumb_text = path.name or str(path).upper().rstrip(os.path.sep)
        btn.setText(crumb_text)
        btn.path = path
        btn.clicked.connect(self.crumb_clicked)
        menu = MenuListView(btn)
        menu.aboutToShow.connect(self.crumb_menu_show)
        menu.setModel(self.fs_model)
        menu.clicked.connect(self.crumb_menuitem_clicked)
        menu.activated.connect(self.crumb_menuitem_clicked)
        btn.setMenu(menu)
        self.crumbs_panel.layout().insertWidget(0, btn)
        btn.setMinimumSize(btn.minimumSizeHint())  # fixed size breadcrumbs
        sp = btn.sizePolicy()
        sp.setVerticalPolicy(sp.Minimum)
        btn.setSizePolicy(sp)
        # print(self._check_space_width(btn.minimumWidth()))
        # print(btn.size(), btn.sizeHint(), btn.minimumSizeHint())

    def crumb_mouse_move(self, event):
        ...
        # print('move!')

    def crumb_menuitem_clicked(self, index):
        "SLOT: breadcrumb menu item was clicked"
        self.set_path(index.data(Qt.EditRole))

    def crumb_clicked(self):
        "SLOT: breadcrumb was clicked"
        self.set_path(self.sender().path)

    def crumb_menu_show(self):
        "SLOT: fill subdirectory list on menu open"
        menu = self.sender()
        self.fs_model.setPathPrefix(str(menu.parent().path) + os.path.sep)

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
        self.path_icon.setPixmap(self.get_icon(self.path_).pixmap(16, 16))
        self.path_selected.emit(self.path_)
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
        arrow = Qt.LeftArrow if layout.count_hidden() > 0 else Qt.RightArrow
        self.btn_root_crumb.setArrowType(arrow)
        # if layout.count_hidden() > 0:
        #     ico = QtGui.QIcon("iconfinder_icon-ios7-arrow-left_211689.png")
        # else:
        #     ico = QtGui.QIcon("iconfinder_icon-ios7-arrow-right_211607.png")
        # self.btn_root_crumb.setIcon(ico)

    def minimumSizeHint(self):
        # print(self.layout().minimumSize().width())
        return QtCore.QSize(150, self.line_address.height())


class StyleProxy(QtWidgets.QProxyStyle):
    win_modern = ("windowsxp", "windowsvista")

    def __init__(self, style, arrow_pix):
        super().__init__(style)
        self.arrow_pix = arrow_pix
        self.stylename = self.baseStyle().objectName()

    def drawPrimitive(self, pe, opt, p: QtGui.QPainter, widget):
        # QToolButton elements:
        # 13: PE_PanelButtonCommand (Fusion) - Fusion button background, called from 15 and 24 calls
        # 15: PE_PanelButtonTool (Windows, Fusion) - left part background (XP/Vista styles do not draw it with `drawPrimitive`)
        # 19: PE_IndicatorArrowDown (Windows, Fusion) - right part down arrow (XP/Vista styles draw it in 24 call)
        # 24: PE_IndicatorButtonDropDown (Windows, XP, Vista, Fusion) - right part background (+arrow for XP/Vista)
        # 
        # Arrow is drawn along with PE_IndicatorButtonDropDown (XP/Vista)
        # https://github.com/qt/qtbase/blob/0c51a8756377c40180619046d07b35718fcf1784/src/plugins/styles/windowsvista/qwindowsxpstyle.cpp#L1406
        # https://github.com/qt/qtbase/blob/0c51a8756377c40180619046d07b35718fcf1784/src/plugins/styles/windowsvista/qwindowsxpstyle.cpp#L666
        # drawBackground paints with DrawThemeBackgroundEx WinApi function
        # https://docs.microsoft.com/en-us/windows/win32/api/uxtheme/nf-uxtheme-drawthemebackgroundex
        if (self.stylename in self.win_modern and
            pe == self.PE_IndicatorButtonDropDown
            ):
            pe = self.PE_IndicatorArrowDown  # see below
        if pe == self.PE_IndicatorArrowDown:
            opt_ = QtWidgets.QStyleOptionToolButton()
            widget.initStyleOption(opt_)
            rc = super().subControlRect(self.CC_ToolButton, opt_,
                                        self.SC_ToolButtonMenu, widget)
            if self.stylename in self.win_modern:
                # By default PE_IndicatorButtonDropDown draws arrow along
                # with right button art. Draw 2px clipped left part instead
                path = QtGui.QPainterPath()
                path.addRect(QtCore.QRectF(rc))
                p.setClipPath(path)
                super().drawPrimitive(self.PE_PanelButtonTool, opt, p, widget)
            # centered square
            rc.moveTop((rc.height() - rc.width()) / 2)
            rc.setHeight(rc.width())
            # p.setRenderHint(p.Antialiasing)
            p.drawPixmap(rc, self.arrow_pix, QtCore.QRect())
        else:
            super().drawPrimitive(pe, opt, p, widget)

    def subControlRect(self, cc, opt, sc, widget):
        rc = super().subControlRect(cc, opt, sc, widget)
        if (self.stylename in self.win_modern and
            sc == self.SC_ToolButtonMenu
            ):
            rc.adjust(-2, 0, 0, 0)  # cut 2 left pixels to create flat edge
        return rc


if __name__ == '__main__':
    from qtapp import QtForm

    class Form(QtWidgets.QDialog):
        _layout_ = QtWidgets.QHBoxLayout
        _loop_ = True

        def perm_err(self, path):
            print('perm err', path)

        def path_err(self, path):
            print('path err', path)
        
        def b_clicked(self):
            pass

        def __init__(self):  # pylint: disable=super-init-not-called
            print(QtWidgets.QStyleFactory.keys())
            # style = QtWidgets.QStyleFactory.create("fusion")
            # self.app.setStyle(style)
            self.address = BreadcrumbsAddressBar()
            self.layout().addWidget(self.address)
            self.address.listdir_error.connect(self.perm_err)
            self.address.path_error.connect(self.path_err)

            if platform.system() == "Windows":
                from platform_win import parse_message, event_device_connection
                def nativeEvent(eventType, message):
                    msg = parse_message(message)
                    devices = event_device_connection(msg)
                    if devices:
                        print("insert/remove device")
                        self.address.update_rootmenu_devices()
                    return False, 0
                self.nativeEvent = nativeEvent


    QtForm(Form)
