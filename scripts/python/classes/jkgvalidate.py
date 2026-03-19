"""
Class that validates a JKG JSON file against the JKG schema.
"""

import os
import io
import itertools
import json as json
import ijson
import jsonschema as jsonschema
import pandas as pd
from loky import get_reusable_executor
from tqdm import tqdm

from .centrallog import CentralLog

class JKGValidate:

    def _load_json(self, dir: str, filename: str) -> dict | list:
        """
        Wraps a read of a JSON file in a tqdm progress bar.
        :param dir: directory path of the JSON file
        :param filename: filename of the JSON file
        """
        file_path = os.path.join(dir, filename)
        self.clog.print_and_logger_info(f"Loading {file_path}...")

        # Get file size in bytes to indicate % complete.
        file_size = os.path.getsize(file_path)
        chunk_size = 1024 * 1024  # 1 MB

        class ProgressReader(io.RawIOBase):
            """
            A custom class inheriting from io.RawIOBase — the base class for
            raw (unbuffered) binary I/O.
            This is needed because io.BufferedReader requires a
            RawIOBase object to wrap.

            """
            def __init__(self, fobj, progress):

                """
                Store the raw file object (fobj)
                and the tqdm progress bar (progress)
                as instance variables.
                """

                self.fobj = fobj
                self.progress = progress

            def readable(self):
                """
                io.RawIOBase.readable() returns False by default.
                io.BufferedReader checks this before doing anything
                and raises UnsupportedOperation if it is False.
                Overriding it to return True tells BufferedReader
                the stream is readable
                """
                return True

            def readinto(self, b):
                """
                The core method io.BufferedReader calls internally. It:
                * Reads up to len(b) bytes from the raw file into the pre-allocated buffer b
                * Gets back n, the number of bytes actually read
                * Updates the tqdm bar by n bytes
                * Returns n so BufferedReader knows how many bytes were filled
                """
                n = self.fobj.readinto(b)
                if n:
                    self.progress.update(n)
                return n

        # Open the file in raw unbuffered mode.
        with open(file_path, 'rb', buffering=0) as raw_f:

            # Create the tqdm progress bar.
            with tqdm(total=file_size, desc=f'Parsing {filename}', unit='B', unit_scale=True,
                      unit_divisor=1024) as progress:
                # Chain ProgressReader into BufferedReader.
                reader = io.BufferedReader(ProgressReader(raw_f, progress), buffer_size=chunk_size)

                # Stream-parse the JSON with ijson
                builder = ijson.common.ObjectBuilder()

                """
                ijson.parse(reader) incrementally parses the JSON,
                emitting (prefix, event, value) tuples as it reads— crucially, 
                it reads through reader (and therefore ProgressReader) 
                so the progress bar updates throughout parsing, 
                not just during a bulk read. 
                ObjectBuilder accumulates those events back into a Python dict/list structure.
                """
                builder = ijson.common.ObjectBuilder()
                for prefix, event, value in ijson.parse(reader):
                    builder.event(event, value)

                return builder.value

    def _validate_top_level(self, JKG, JKG_Schema):
        # Validate JKG against top level of JKG_Schema
        self.clog.print_and_logger_info("Validating JKG JSON file against the JKG schema.")
        try:
            jsonschema.validate(JKG, JKG_Schema)
            self.clog.print_and_logger_info("JKG data has nodes and rels lists.")
        except jsonschema.exceptions.ValidationError as e:
            self.clog.print_and_logger_error(f"JKG data is INVALID: {e.message}")
            raise(e)

    def _validate_json(self):
        """
        Validates the JKG JSON file against the JKG schema.

        """
        self.clog.print_and_logger_info("Validating JKG JSON file against the JKG schema.")

        # Load JKG JSON and JKG schema.
        JKG = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_file)
        JKG_Schema = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_schema)

        self._validate_top_level(JKG, JKG_Schema)


    def __init__(self, jkg_json_dir: str, jkg_json_file: str,
                 jkg_schema_json: str, clog: CentralLog):
        """

        :param jkg_json_dir: path to the JKG JSON file
        :param jkg_json_file: filename of the JKG JSON file
        :param jkg_schema_json: filename of the JKG schema JSON file
        :param clog: the central logging object
        """
        self.jkg_json_dir = jkg_json_dir
        self.jkg_json_file = jkg_json_file
        self.jkg_json_schema = jkg_schema_json
        self.clog = clog

        self._validate_json()

