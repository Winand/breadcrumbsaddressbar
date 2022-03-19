"""
Abstract superclass for all data providers
"""

import abc
from pathlib import Path
from qtpy import QtGui, QtCore
from qtpy.QtWidgets import QWidget, QCompleter


class QABCMeta(abc.ABCMeta, type(QtCore.QObject)):
    "https://stackoverflow.com/q/28799089/python-abc-multiple-inheritance"


class DataModel(QtCore.QStringListModel, metaclass=QABCMeta):
    """
    Provides data for QCompleter and breadcrumb menus
    """
    @abc.abstractmethod
    def setPathPrefix(self, prefix: str):
        "Prefix sets path level to be used in data model"
        raise NotImplementedError


class DataProvider(abc.ABC):
    """
    Interface class for data providers
    """
    # @override decorator could be implemented: https://stackoverflow.com/q/1167617
    model: DataModel

    @abc.abstractmethod
    def check_path(self, path: Path):
        "Checks passed path and returns it optionally applying transformations"
        # abstract+not impl https://stackoverflow.com/q/44315961#comment108547950_44316063
        raise NotImplementedError

    @abc.abstractmethod
    def get_devices(self):
        "Returns list of available devices"
        raise NotImplementedError

    def get_icon(self, path: Path):
        "Returns icon for passed path - default is empty icon"
        return QtGui.QIcon()

    def get_places(self):
        "Returns list of places like Home, Destop, etc"
        raise NotImplementedError

    def init_completer(self, edit_widget: QWidget) -> QCompleter:
        "Init QCompleter to work with passed QWidget"
        raise NotImplementedError
