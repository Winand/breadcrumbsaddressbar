"""
Define platform-specific functions with decorators
https://stackoverflow.com/a/60244993
"""

import platform
import sys
from typing import Union as U


class _Not_Implemented:
    def __init__(self, func_name):
        self.func_name = func_name

    def __call__(self, *args, **kwargs):
        raise NotImplementedError(
            f"Function {self.func_name} is not defined "
            f"for platform {platform.system()}."
        )


def if_platform(*plat: U[str, list[str], tuple[str]]):
    frame = sys._getframe().f_back
    def _ifdef(func=None):
        nonlocal plat
        if isinstance(plat, str):
            plat = plat,
        if platform.system() in plat:
            return func or True
        if func.__name__ in frame.f_locals:
            return frame.f_locals[func.__name__]
        return _Not_Implemented(func.__name__)
    return _ifdef
