from unittest import TestCase

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from breadcrumbsaddressbar import BreadcrumbsAddressBar


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
        self.app = QApplication.instance() or QApplication([])
        self.form = Form()
        self.form.show()
        # self.form.resize(640, 0)
        return super().setUp()

    def test_switch_edit_mode(self):
        "Test edit mode enter and exit"
        self.assertFalse(self.form.w.line_address.isVisible())
        # Enter edit mode on click
        QTest.mouseClick(self.form.w.switch_space, Qt.MouseButton.LeftButton)
        self.assertTrue(self.form.w.line_address.isVisible())
        # Exit edit mode on escape
        QTest.keyClick(self.form.w.line_address, Qt.Key.Key_Escape)
        self.assertFalse(self.form.w.line_address.isVisible())

    def test_type_and_set_path(self):
        "Test type and set path"
        # Enter edit mode
        QTest.mouseClick(self.form.w.switch_space, Qt.MouseButton.LeftButton)
        # Enter new path
        QTest.keyClicks(self.form.w.line_address, 'C:\\')
        QTest.keyClick(self.form.w.line_address, Qt.Key.Key_Enter)
        self.assertFalse(self.form.w.line_address.isVisible())
        self.assertEqual(str(self.form.w.path()), "C:\\")


if __name__ == '__main__':
    import unittest
    unittest.main()
