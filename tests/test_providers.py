import os
from pathlib import Path
from unittest import TestCase

from breadcrumbsaddressbar.backend.dictionary import Dictionary
from breadcrumbsaddressbar.backend.filesystem import Filesystem


class TestProviders(TestCase):
    """
    Providers tests
    """
    def test_places(self):
        prov_d = Dictionary({"/": "icon=SP_DirIcon", "/metadata": {"places": {"root": "/"}}})
        places = list(prov_d.get_places())
        self.assertEqual(len(places), 1)
        self.assertEqual(places[0][0], "root")
        self.assertEqual(places[0][1], "/")
        # self.assertEqual(places[0][2], "icon=SP_DirIcon")
