"""
Class that represents the common configuration file.
The common configuration file is optimized for use by Shell scripts.
It is not in the INI format supported by Python's native ConfigParser module.
"""

from configobj import ConfigObj

class ConfigFile:

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.config = ConfigObj(self.filename)