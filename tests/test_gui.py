from unittest import TestCase

from breadcrumbsaddressbar import BreadcrumbsAddressBar
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtTest import QTest


class Form(QtWidgets.QDialog):
    "Top level container for the widget"
    def __init__(self):
        super().__init__()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.w = BreadcrumbsAddressBar()
        self.layout().addWidget(self.w)


class TestGUI(TestCase):
    """
    Test GUI functionality
    """
    def setUp(self) -> None:
        self.app = QtWidgets.QApplication([])
        self.form = Form()
        self.form.show()
        # self.form.resize(640, 0)
        return super().setUp()

    def test_switch_edit_mode(self):
        "Test edit mode enter and exit"
        self.assertFalse(self.form.w.line_address.isVisible())
        # Enter edit mode on click
        QTest.mouseClick(self.form.w.switch_space, QtCore.Qt.LeftButton)
        self.assertTrue(self.form.w.line_address.isVisible())
        # Exit edit mode on escape
        QTest.keyClick(self.form.w.line_address, QtCore.Qt.Key_Escape)
        self.assertFalse(self.form.w.line_address.isVisible())

    def test_type_and_set_path(self):
        "Test type and set path"
        # Enter edit mode
        QTest.mouseClick(self.form.w.switch_space, QtCore.Qt.LeftButton)
        # Enter new path
        QTest.keyClicks(self.form.w.line_address, 'C:\\')
        QTest.keyClick(self.form.w.line_address, QtCore.Qt.Key_Enter)
        self.assertFalse(self.form.w.line_address.isVisible())
        self.assertEqual(str(self.form.w.path()), "C:\\")


if __name__ == '__main__':
    import unittest
    unittest.main()
