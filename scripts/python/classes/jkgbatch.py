"""
Class that splits a large file in JSON Knowledge Graph format into sets of the
following types of files:
- nodes
- rels other than CODE
- CODE rels

Each file in a set will contain a number of nodes up to a value specified at
instantiation.
"""

import ijson
import os
import shutil

from .centrallog import CentralLog

class JKGBatch:

    def _mkdir_clean(self, path: str):
        """
        Create a directory at `path`.
        - If it already exists: delete it entirely and recreate it.
        - If it does not exist: create it fresh.
        """
        if os.path.exists(path):
            self.clog.print_and_logger_info('Deleting existing path: ' + path)
            shutil.rmtree(path)  # Delete folder and ALL contents recursively

        self.clog.print_and_logger_info('Creating new path: ' + path)
        os.makedirs(path)  # Always recreate

    def _split_json(self):

        self.clog.print_and_logger_error(f'Processing JKG JSON file:  {self.jkg_json_file}')
        batch_path = os.path.join(self.jkg_json_dir, 'batch')
        self._mkdir_clean(batch_path)



    def __init__(self, jkg_json_dir: str, jkg_json_file: str,
                 jkg_batch_size: int, clog: CentralLog):
        """

        :param jkg_json_dir: path to the JKG JSON file
        :param jkg_json_file: filename of the JKG JSON file
        :param jkg_batch_size: size of each batch--i.e., the maximum number of
               objects that should be in each split file
        :param clog: the central logging object
        """
        self.jkg_json_dir = jkg_json_dir
        self.jkg_json_file = jkg_json_file
        self.jkg_batch_size = jkg_batch_size
        self.clog = clog

        self._split_json()

