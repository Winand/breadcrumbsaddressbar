import os
from pathlib import Path
from unittest import TestCase

from breadcrumbsaddressbar.backend.dictionary import Dictionary
from PyQt5 import QtWidgets, QtGui, QtCore


class TestDictionary(TestCase):
    """
    Dictionary data provider tests
    """
    def setUp(self) -> None:
        self.app = QtWidgets.QApplication([])
        return super().setUp()

    def test_root_directory(self):
        "Root directory '/' test"
        # Root directory on the root level
        Dictionary({"/": {"subfolder1": None}})
        # Root directory on a deeper level raises ValueError
        self.assertRaises(ValueError, Dictionary, {"home": {"/": None}})

    def test_set_prefix(self):
        "Test setPathPrefix method"
        dict_prov = Dictionary({"/": {"subfolder1": None}})
        dict_prov.model.setPathPrefix("/")
        self.assertEqual(dict_prov.model.current_path, Path(os.path.sep))

    def test_places(self):
        """
        get_places iterates over (name, path) tuples
        Additionally check path icon
        """
        test_icon = self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        prov_d = Dictionary({"/": "icon=SP_MediaPlay", "/metadata": {"places": {"root": "/"}}})
        places = list(prov_d.get_places())
        self.assertEqual(len(places), 1)
        self.assertEqual(places[0][0], "root")
        self.assertEqual(places[0][1], "/")
        # https://forum.qt.io/topic/15305/how-can-i-compare-2-icons
        self.assertEqual(prov_d.get_icon(Path("/")).pixmap(32, 32).toImage(),
                         test_icon.pixmap(32, 32).toImage())
