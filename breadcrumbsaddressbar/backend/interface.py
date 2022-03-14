"""
Abstract superclass for all data providers
"""

import abc
from pathlib import Path
from qtpy.QtWidgets import QWidget, QCompleter


class DataProvider(abc.ABC):
    """
    Interface class for data providers
    """
    # @override decorator could be implemented: https://stackoverflow.com/q/1167617

    @abc.abstractmethod
    def check_path(self, path: Path):
        "Checks passed path and returns it optionally applying transformations"
        # abstract+not impl https://stackoverflow.com/q/44315961#comment108547950_44316063
        raise NotImplementedError

    @abc.abstractmethod
    def get_devices(self):
        "Returns list of available devices"
        raise NotImplementedError

    def get_places(self):
        "Returns list of places like Home, Destop, etc"
        raise NotImplementedError

    def init_completer(self, edit_widget: QWidget) -> QCompleter:
        "Init QCompleter to work with passed QWidget"
        raise NotImplementedError
