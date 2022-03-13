from io import TextIOBase
from pathlib import Path

import yaml

from .dictionary import Dictionary


class YamlDict(Dictionary):
    """
        Subclass of Dictionary that reads a yaml file or string.
    """
    def __init__(self, yaml_src: "Path|TextIOBase|str"):
        if isinstance(yaml_src, Path):
            with open(yaml_src, "r") as f:
                data = yaml.safe_load(f)
        elif isinstance(yaml_src, (TextIOBase, str)):
            data = yaml.safe_load(yaml_src)
        else:
            raise TypeError(
                f"yaml_src must be a Path, TextIOBase, or str, not {type(yaml_src)}"
            )
        super().__init__(data)
