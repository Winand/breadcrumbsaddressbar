import platform

from qtpy import QtWidgets

from breadcrumbsaddressbar import BreadcrumbsAddressBar
from breadcrumbsaddressbar.platform_common import if_platform

if platform.system() == "Windows":
    from breadcrumbsaddressbar.platform_win import (event_device_connection,
                                                    parse_message)


if __name__ == '__main__':
    class Form(QtWidgets.QDialog):
        def perm_err(self, path):
            print('perm err', path)

        def path_err(self, path):
            print('path err', path)

        def __init__(self):  # pylint: disable=super-init-not-called
            print(QtWidgets.QStyleFactory.keys())
            # style = QtWidgets.QStyleFactory.create("fusion")
            # self.app.setStyle(style)
            super().__init__()
            self.setLayout(QtWidgets.QHBoxLayout())
            self.address = BreadcrumbsAddressBar()
            self.layout().addWidget(self.address)
            self.address.listdir_error.connect(self.perm_err)
            self.address.path_error.connect(self.path_err)

        @if_platform('Windows')
        def nativeEvent(self, eventType, message):
            msg = parse_message(message)
            devices = event_device_connection(msg)
            if devices:
                print("insert/remove device")
                self.address.update_rootmenu_devices()
            return False, 0


    app = QtWidgets.QApplication([])
    form = Form()
    form.exec_()
