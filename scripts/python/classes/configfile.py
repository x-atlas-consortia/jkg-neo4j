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

    def get(self, key: str) -> str:
        """
        Gets a value from the config file by key.
        :param key: the config key to look up
        :return: the value associated with the key
        :raises KeyError: if the key is not found in the config file
        """
        if key not in self.config:
            raise KeyError(f"Required config key '{key}' not found in '{self.filename}'")
        return self.config[key]