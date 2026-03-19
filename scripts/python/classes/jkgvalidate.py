"""
Class that validates a JKG JSON file against the JKG schema.
"""

import os
import io
import contextlib

import json as json
import ijson
import jsonschema as jsonschema
from jsonschema import Draft202012Validator
import pandas as pd

from loky import get_reusable_executor
from tqdm import tqdm

from .centrallog import CentralLog
# Timer for lazy event process monitoring
from .jkg_timer import JkgTimer

class JKGValidate:

    def _load_json(self, dir: str, filename: str) -> dict | list:
        """
        Wraps a read of a JSON file in a tqdm progress bar.
        :param dir: directory path of the JSON file
        :param filename: filename of the JSON file
        """
        file_path = os.path.join(dir, filename)

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

    def _validate_against_top_level(self):

        # Validate JKG against top level of JKG_Schema.
        jtimer = JkgTimer(display_msg=f"Validating against the top-level JKG schema")

        v = Draft202012Validator(self.JKG_Schema)
        errors = sorted(v.iter_errors(self.JKG), key=lambda e: e.path)
        for error in errors:
            self.clog.print_and_logger_error(error.message)

        jtimer.stop()

    def _validate_items_against_schema(self, items: list, s:int, f:int, schema: dict, sname: str):
        """
        Validates a set of nodes from the JKG JSON against the specified
        schema.
        :param items: a slice of a list of JKG JSON nodes
        :param s: start node identifier
        :param f: finish node identifier
        :param schema: part of a JSON schema
        :param sname: name of the schema
        :return:
        """

        try:
            jsonschema.validate(items, schema)
            self.clog.print_and_logger_info(f"Processed successfully nodes: {s} to {f}")
        except jsonschema.exceptions.ValidationError as e:
            self.clog.print_and_logger_error(f"Processing nodes: {s} to {f}")
            self.clog.print_and_logger_error(f"INVALID: node row: {e.json_path}, {e.message}")

    def _validate_nodes_against_schema(self, nodetype: str):

        """
        Validates a set of nodes from the JKG JSON against the specified schema.
        :param nodetype: type of node - e.g., "nodes", "rels"

        """

        max_index = len(self.JKG[nodetype]) - 1
        max_index = 2000 # debug
        executor = get_reusable_executor(max_workers=10, timeout=3)
        self.clog.print_and_logger_info(f"Schema validation begins for {nodetype} 0 to {max_index}")
        self.clog.print_and_logger_info("In each 1000 nodes up to one invalid node is flagged.")

        for i in range(int(max_index / 1000)):

            s = i * 1000
            f = s + 1000
            # Start timer.
            jtimer = JkgTimer(display_msg=f"Validating nodes {s} to {f} against {nodetype} schema")

            executor.submit(self._validate_items_against_schema(), self.JKG[nodetype][s:f], s, f)
            # End timer.
            jtimer.stop()

        s = int(max_index / 1000) * 1000
        f = s + (max_index % 1000)
        # Start timer.
        jtimer = JkgTimer(display_msg=f"Validating nodes {s} to {f} against {nodetype} schema")
        executor.submit(self._validate_items_against_schema(), self.JKG[nodetype][s:f], s, f, nodetype)
        jtimer.stop()

    def _validate_json(self):

        """
        Validates the JKG JSON file against the JKG schema.

        """
        self.clog.print_and_logger_info("Validating JKG JSON file against the JKG schema.")

        #self._validate_against_top_level()_top_level()
        self._validate_nodes_against_schema(nodetype='nodes')
        self._validate_nodes_against_schema(nodetype='rels')

    def _parse_jkg_files(self):

        # Parse JKG JSON and JKG schema.
        self.clog.print_and_logger_warning("The historical time to parse the JKG.JSON is under 6 minutes.")
        self.JKG = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_file)
        self.JKG_Schema = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_schema)


    def _load_nodes_rels_dataframe(self):

        self.clog.print_and_logger_info("Loading JKG JSON into dataframes.")
        # Validate JKG against top level of JKG_Schema.
        self.clog.print_and_logger_warning("The historical time to load rels is under 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Loading rels")
        rels = pd.DataFrame(self.JKG['rels'])
        jtimer.stop()
        self.clog.print_and_logger_warning("The historical time to load nodes is under 30 seconds.")
        jtimer = JkgTimer(display_msg=f"Loading nodes")
        nodes = pd.DataFrame(self.JKG['nodes'])
        jtimer.stop()

        #df = pd.json_normalize(rels)
        # Normalize the JSON arrays to flat tables.

        self.clog.print_and_logger_warning("The historical time to normalize rels start is under 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels start")
        starts = pd.json_normalize(rels.start)
        jtimer.stop()

        self.clog.print_and_logger_warning("The historical time to normalize rels end is under 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels end")
        ends = pd.json_normalize(rels.end)
        jtimer.stop()

        self.clog.print_and_logger_warning("The historical time to normalize rels properties is under 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels properties")
        df = pd.json_normalize(rels.properties)
        jtimer.stop()

        df = pd.concat([rels.label.reset_index(drop=True), df.reset_index(drop=True)], axis=1)
        self.rels = df

        self.clog.print_and_logger_warning("The historical time to normalize nodes properties is under 1 minute.")
        jtimer = JkgTimer(display_msg=f"Normalizing nodes properties")
        df = pd.json_normalize(nodes.properties)
        jtimer.stop()

        df = pd.concat([nodes.labels.reset_index(drop=True), df.reset_index(drop=True)], axis=1)
        self.nodes = df

    def _log_duplicates(self, duplicates: pd.DataFrame, items: str, filename: str):

        """
        Writes the contents of a DataFrame to a CSV file.
        :param duplicates: DataFrame of duplicate information.
        :param items: name of the duplicate items
        :param filename: output filename

        """
        dupfile = os.path.join(self.jkg_json_dir, filename)
        if duplicates.empty:
            self.clog.print_and_logger_info(f"All {items} are unique.")
            with contextlib.suppress(FileNotFoundError):
                os.remove(dupfile)
        else:
            self.clog.print_and_logger_error(f"Writing duplicate {items} to {filename}")
            duplicates.to_csv(dupfile, index=False)


    def _validate_nodes_for_uniqueness(self):

        # Validate Uniqueness of node ids, sabs, node_labels, rel_labels

        self.clog.print_and_logger_info("Validating nodes for uniqueness.")

        # Check duplicate node id
        duplicates = self.nodes[self.nodes.duplicated(subset=['id'], keep=False)]
        dupfile = os.path.join(self.jkg_json_dir, 'duplicate_node_ids.csv')
        self._log_duplicates(duplicates=duplicates, items='node ids',
                             filename='duplicate_node_ids.csv')

        # Subset nodes to Source and Check duplicate sab
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Source' in x)]
        duplicates = fdf[fdf.duplicated(subset=['sab'], keep=False)]
        dupfile = os.path.join(self.jkg_json_dir, 'duplicate_SABs.csv')
        self._log_duplicates(duplicates=duplicates, items='Source SABs',
                             filename='duplicate_sabs.csv')

        # Subset nodes to Node_Label and Check duplicate node_label
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Node_Label' in x)]
        duplicates = fdf[fdf.duplicated(subset=['node_label'], keep=False)]
        dupfile = os.path.join(self.jkg_json_dir, 'duplicate_node_labels.csv')
        self._log_duplicates(duplicates=duplicates, items='Node_Label node_labels',
                             filename='duplicate_node_labels.csv')

        # Subset nodes to Rel_Label and Check duplicate rel_label
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Rel_Label' in x)]
        duplicates = fdf[fdf.duplicated(subset=['rel_label'], keep=False)]
        dupfile = os.path.join(self.jkg_json_dir, 'duplicate_rel_labels.csv')
        self._log_duplicates(duplicates=duplicates, items='Rel_Label rel_labels',
                             filename='duplicate_rel_labels.csv')

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

        # Parse JKG files.
        self.clog.print_and_logger_warning('Historical estimates are for the UMLS JKG.JSON (4.3 GB).')
        self._parse_jkg_files()

        # Load nodes and rels arrays from JKG JSON into Pandas.
        self._load_nodes_rels_dataframe()
        # Validate node uniqueness.
        self._validate_nodes_for_uniqueness()

        self._validate_json()

