"""
breadcrumbsaddressbar sample application
"""

import platform
from pathlib import Path

from qtpy import QtWidgets

from breadcrumbsaddressbar import BreadcrumbsAddressBar
from breadcrumbsaddressbar.backend.yamldict import YamlDict
from breadcrumbsaddressbar.platform.common import if_platform

if platform.system() == "Windows":
    from breadcrumbsaddressbar.platform.windows import (
        event_device_connection, parse_message)


class Form(QtWidgets.QDialog):
    """
    Sample widget to show how to use the address bar
    """
    def perm_err(self, path):
        "Slot called on permission error"
        print('perm err', path)

    def path_err(self, path):
        "Slot called if path does not exists"
        print('path err', path)

    def __init__(self):  # pylint: disable=super-init-not-called
        print(QtWidgets.QStyleFactory.keys())
        # style = QtWidgets.QStyleFactory.create("fusion")
        # self.app.setStyle(style)
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.resize(480, 0)

        # YAML file based address bar
        self.address = BreadcrumbsAddressBar(backend=YamlDict(Path("model_data.yaml")))
        self.layout().addWidget(self.address)
        self.address.listdir_error.connect(self.perm_err)
        self.address.path_error.connect(self.path_err)

        # File system address bar
        self.address2 = BreadcrumbsAddressBar()
        self.layout().addWidget(self.address2)
        self.address2.listdir_error.connect(self.perm_err)
        self.address2.path_error.connect(self.path_err)

    @if_platform('Windows')
    def nativeEvent(self, eventType, message):  # pylint: disable=invalid-name
        """
        Auto-update address bar device list (Windows only)
        """
        msg = parse_message(message)
        devices = event_device_connection(msg)
        if devices:
            print("insert/remove device")
            self.address.update_rootmenu_devices()
        return False, 0


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    form = Form()
    form.exec_()
