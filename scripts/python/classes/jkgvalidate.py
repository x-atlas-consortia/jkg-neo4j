"""
Class that validates JKG JSON files against the JKG schema.
"""

# Used for file management
import io
import os
import contextlib
from pathlib import Path

# JSON streaming
import ijson
# Custom validation (duplicates, referential integrity)
import pandas as pd
# Progress monitoring
from tqdm import tqdm

# JSON schema validation
import jsonschema as jsonschema
from jsonschema import Draft202012Validator
from loky import get_reusable_executor
from loky import as_completed

# Common configuration
from .configfile import ConfigFile

# Centralized application logging
from .centrallog import CentralLog

# Timer for lazy event process monitoring
from .jkg_timer import JkgTimer

# File reading
from .progressreader import ProgressReader

class JKGValidate:

    def __init__(self, cfg: ConfigFile, clog: CentralLog):
        """
        :param cfg: the common config file object
        :param clog: the central logging object
        """

        # Application log
        self.clog = clog

        # Determine whether the schema validation type should
        # use parallel processing on batched files.
        self.parallel = cfg.get('schema_validation_parallel')=='true'

        # Get the validation parallel processing chunk size.
        self.jkg_validate_chunk = int(cfg.get('jkg_validate_chunk'))
        if self.parallel and self.jkg_validate_chunk < 10:
            self.clog.print_and_logger_warning(f"A small chunk size of {self.jkg_validate_chunk} is likely to result "
                                               f"in timeout errors or other issues from parallel processing. "
                                               f"The recommended minimum chunk size is 100.")

        # Get the flags for structural validation.
        self.check_uniqueness = cfg.get('check_uniqueness')=='true'
        self.check_referential_integrity = cfg.get('check_referential_integrity')=='true'

        # Get the path to the JKG JSON source file and schema.
        self.jkg_json_dir = cfg.get('jkg_json_dir')
        self.jkg_json_file = cfg.get('jkg_json_file')
        self.jkg_schema_json = cfg.get('jkg_schema_json')

        # Get the file of the schema validation.
        self.schema_validation_error_file = cfg.get('schema_validation_error_file')
        self.schema_validation_error_path = os.path.join(self.jkg_json_dir, self.schema_validation_error_file)

        # Delete previous instances of the schema validation error CSV.
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.schema_validation_error_path)

        self.JKG_Schema = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_schema_json)

        if self.check_uniqueness | self.check_referential_integrity:
            # Parse JKG JSON.
            self.clog.print_and_logger_warning('Historical time estimates are based on the UMLS JKG.JSON (4+ GB).')
            self._parse_jkg_files()
            self._validate_json_structurally()

        # Validate JSON against schema.
        self._validate_json_against_schema()

    def _validate_json_structurally(self):
        """
        Validates a JKG JSON file for structural fitness, including:
        1. Uniqueness
        2. Referential integrity

        Structural validation can only work with the entire JKG JSON file.
        """

        # Load nodes and rels arrays from JKG JSON into Pandas.
        self._load_nodes_rels_dataframe()

        if self.check_uniqueness:
            # Validate node uniqueness.
            self._validate_nodes_for_uniqueness()
        if self.check_referential_integrity:
            # Validate referential integrity.
            self._validate_referential_integrity()

    def _parse_jkg_files(self):

        """
        Parse JKG JSON file and JKG schema file.
        """

        self.clog.print_and_logger_warning("Historical time to parse JKG.JSON: < 6 minutes.")
        self.JKG = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_file)
        #self.JKG_Schema = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_schema_json)

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

    def _load_nodes_rels_dataframe(self):

        self.clog.print_and_logger_info("Loading JKG JSON into dataframes.")
        self.clog.print_and_logger_warning("Historical time to load rels: < 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Loading rels")
        rels = pd.DataFrame(self.JKG['rels'])
        jtimer.stop()
        self.clog.print_and_logger_warning("Historical time to load nodes: < 30 seconds.")
        jtimer = JkgTimer(display_msg=f"Loading nodes")
        nodes = pd.DataFrame(self.JKG['nodes'])
        jtimer.stop()

        #df = pd.json_normalize(rels)
        # Normalize the JSON arrays to flat tables.

        self.clog.print_and_logger_warning("Historical time to normalize rels start: < 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels start")
        self.starts = pd.json_normalize(rels.start)
        jtimer.stop()

        self.clog.print_and_logger_warning("Historical time to normalize rels end: < 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels end")
        self.ends = pd.json_normalize(rels.end)
        jtimer.stop()

        self.clog.print_and_logger_warning("Historical time to normalize rels properties: < 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels properties")
        df = pd.json_normalize(rels.properties)
        jtimer.stop()

        df = pd.concat([rels.label.reset_index(drop=True), df.reset_index(drop=True)], axis=1)
        self.rels = df

        self.clog.print_and_logger_warning("Historical time to normalize nodes properties: < 1 minute.")
        jtimer = JkgTimer(display_msg=f"Normalizing nodes properties")
        df = pd.json_normalize(nodes.properties)
        jtimer.stop()

        df = pd.concat([nodes.labels.reset_index(drop=True), df.reset_index(drop=True)], axis=1)
        self.nodes = df

    def _log_issue(self, issue_frame: pd.DataFrame, noerrmsg: str, filename: str):

        """
        Writes missing or duplicate items to a CSV file.
        :param issue_frame: DataFrame of issues.
        :param noerrmsg: message to display in log in case of no issues
        :param filename: output file
        """

        issuefile = os.path.join(self.jkg_json_dir, filename)
        if issue_frame.empty:
            self.clog.print_and_logger_info(noerrmsg)
            with contextlib.suppress(FileNotFoundError):
                os.remove(issuefile)
        else:
            self.clog.print_and_logger_error(f"Writing issues to {filename}")

            chunk_size = 1000
            chunks = [issue_frame[i:i + chunk_size] for i in range(0, len(issue_frame), chunk_size)]
            chunks.columns = ['id']

            for i, chunk in enumerate(tqdm(chunks, desc="Writing issues")):
                chunk.to_csv(issuefile, mode='w', index=False, header=(i == 0))

    def _validate_nodes_for_uniqueness(self):

        """
        Validate nodes for uniqueness.
        """
        # Validate Uniqueness of node ids, sabs, node_labels, rel_labels

        self.clog.print_and_logger_info("Validating nodes for uniqueness.")

        # Check duplicate node id
        duplicates = self.nodes[self.nodes.duplicated(subset=['id'], keep=False)]
        self._log_issue(issue_frame=duplicates,
                        noerrmsg='All node ids are unique.',
                        filename='duplicate_node_sab.csv')

        # Subset nodes to Source and Check duplicate sab
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Source' in x)]
        duplicates = fdf[fdf.duplicated(subset=['sab'], keep=False)]
        self._log_issue(issue_frame=duplicates,
                        noerrmsg='All Source SABs are unique.',
                        filename='duplicate_sabs.csv')

        # Subset nodes to Node_Label and Check duplicate node_label
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Node_Label' in x)]
        duplicates = fdf[fdf.duplicated(subset=['node_label'], keep=False)]
        self._log_issue(issue_frame=duplicates,
                        noerrmsg='All node labels are unique.',
                        filename='duplicate_node_labels.csv')

        # Subset nodes to Rel_Label and Check duplicate rel_label
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Rel_Label' in x)]
        duplicates = fdf[fdf.duplicated(subset=['rel_label'], keep=False)]
        self._log_issue(issue_frame=duplicates,
                        noerrmsg='All rel_labels are unique.',
                        filename='duplicate_rel_labels.csv')

    def _validate_referential_integrity(self):
        """
        Validates nodes and rels for referential integrity.
        :return:
        """
        # Check if all values in list_a are in list_b
        # missing_values = list_a[~list_a.isin(list_b)]

        self.clog.print_and_logger_info("Validating referential integrity.")

        # Reports Node sab NOT in Source sab list
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Source' in x)]
        u_sab = pd.Series(fdf['sab'])
        nodes_sab = pd.Series(self.nodes['sab'].unique()).dropna()  # drop NaN because Term nodes have no sab
        missing_values = nodes_sab[~nodes_sab.isin(u_sab)]
        self._log_issue(issue_frame=missing_values,
                          noerrmsg='All Node sabs are present in Source sabs.',
                          filename='missing_node_sab.csv')

        # Reports Rel sab NOT in Source sab list - uses Source sab list u_sab from above
        rels_sab = pd.Series(self.rels['sab'].unique())
        missing_values = rels_sab[~rels_sab.isin(u_sab)]
        self._log_issue(issue_frame=missing_values,
                          noerrmsg='All Rel sabs are present in Source sabs.',
                          filename='missing_rel_sab.csv')

        # Reports Concept other Labels NOT in node_label list with Concept added
        fdf = self.nodes[self.nodes['labels'].apply(lambda x: 'Concept' in x)]
        u_labels = pd.Series(fdf['labels'].explode().unique())
        node_labels_concept = pd.concat([self.nodes.node_label, pd.Series(['Concept'])], ignore_index=True)
        missing_values = u_labels[~u_labels.isin(node_labels_concept)]
        self._log_issue(issue_frame=missing_values,
                          noerrmsg='All Concept Labels are present in node_label.',
                          filename='missing_concept_label.csv')

        # Reports Rel label NOT in rel_label list with CODE added
        rel_labels_CODE = pd.concat([self.nodes.rel_label, pd.Series(['CODE'])], ignore_index=True)
        u_labels = pd.Series(self.rels['label'].unique())
        missing_values = u_labels[~u_labels.isin(rel_labels_CODE)]
        self._log_issue(issue_frame=missing_values,
                          noerrmsg='All Rel labels are present in rel_label.',
                          filename='missing_rel_label.csv')

        # Reports start property.id of rels in node id list
        u_labels = self.starts['properties.id']
        missing_values = u_labels[~u_labels.isin(self.nodes.id)]
        self._log_issue(issue_frame=missing_values,
                          noerrmsg='All Rel start id are present in node id.',
                          filename='missing_rel_start.csv')

        # Reports end property.id of rels in node id list
        u_labels = self.ends['properties.id']
        missing_values = u_labels[~u_labels.isin(self.nodes.id)]
        self._log_issue(issue_frame=missing_values,
                          noerrmsg='All Rel end id are present in node id.',
                          filename='missing_rel_end.csv')

    def _format_validation_error(self, error, items: list) -> str:

        """
        Formats a jsonschema ValidationError into a human-readable message.
        :param error: a jsonschema ValidationError (a deque)
        :param items: the slice of items being validated
        :return: tab-delimited error message
        """
        path = list(error.absolute_path)
        msg = error.message

        item = ''
        if path and isinstance(path[0], int):
            item = items[path[0]]

        return f'{msg}\t{item}'

    def _write_validation_errors(self, validation_errors: set, mode:str='w'):
        """
        Writes formatted validation errors to a tab-separated variables file.
        :param validation_errors: set of validation errors

        """

        if not validation_errors:
            return

        dferr = pd.DataFrame(list(validation_errors))
        # Each error string is tab-delimited.
        # Split error message from item.
        dferr = dferr[0].str.split('\t', expand=True)
        dferr.columns = ['error', 'item']

        dferr = dferr.sort_values(by=['item','error'], ascending=True)

        if os.path.exists(self.schema_validation_error_path):
            # Because the file is deleted before each validation run,
            # the presence of the file means that it is for the current run.
            mode = 'a'

        else:
            mode = 'w'

        header = mode == 'w'

        dferr.to_csv(self.schema_validation_error_path, index=False, sep='\t', mode=mode, header=header)

    def _validate_entire(self):

        # Validate entire JKG JSON against the JKG_Schema.
        jtimer = JkgTimer(display_msg=f"Validation of entire JKG JSON against entire JKG schema")
        validation_errors = self._validate_items_against_schema(items=self.JKG, schema=self.JKG_Schema)
        jtimer.stop()
        self._write_validation_errors(validation_errors=validation_errors)

    def _validate_items_against_schema(self, items: list, schema: dict) -> set:
        """
        Validates a set of nodes from the JKG JSON against the specified
        schema.
        :param items: list of JKG JSON nodes, up to the entire array in JKG JSON.
        :param schema: part or all of a JSON schema

        :return: Python set of unique error messages per validation
        """

        # Use a validator class in order to obtain details on validation errors.
        v = Draft202012Validator(schema)
        errors = sorted(v.iter_errors(items), key=lambda e: e.path)
        return {self._format_validation_error(error=error, items=items) for error in errors}

    def _validate_batched_json_files(self):
        """
        Validates a set of batched JKG JSON files against the JKG Schema.
        """

        self.clog.print_and_logger_info(
            f"Parallel processing chunk size = {self.jkg_validate_chunk}.")

        batch_path = Path(os.path.join(self.jkg_json_dir, 'batch'))

        for filepath in sorted(batch_path.iterdir()):
            if filepath.is_file():
                # Get the type from the file name.
                if '_node' in filepath.name:
                    arraykey = 'nodes'
                else:
                    arraykey = 'rels'

                #self.clog.print_and_logger_info(f'Validating {filepath.name} for {arraykey}.')

                self._validate_parallel(arraykey=arraykey, filepath=filepath)

    def _validate_parallel(self, arraykey: str, filepath: Path):

        """
        Validates an array (e.g., nodes) from a JKG JSON file against
        an associated subschema of JKG Schema (i.e., just the nodes subschema),
        using parallel processing.

        :param arraykey: type of node - e.g., "nodes", "rels"
        :param filepath: path to JKG JSON batch file

        """

        # Set up parallel processing chunking parameters.

        # Initialize lower bound of chunking
        s = 0

        # while loop control:
        # Parse the batch JSON file.
        batch_dir = os.path.join(self.jkg_json_dir, 'batch')
        batch_json=self._load_json(dir=batch_dir, filename=filepath.name)
        max_index = len(batch_json[arraykey]) - 1

        # for tqdm pbar
        num_chunks = (max_index + self.jkg_validate_chunk - 1) // self.jkg_validate_chunk

        # Set up parallel processing:
        # Loky executor and parallel worker processes
        executor = get_reusable_executor(max_workers=10, timeout=3)

        # Returns from parallel validation processes.
        # Loky assigns these a type of "future".
        # Futures are like JavaScript promises.
        validation_futures = []
        chunk_ranges = []

        while s < max_index:
            # Set upper bound of chunk.
            f = min(s + self.jkg_validate_chunk, max_index)

            # Chunk = slice of nodes from array
            # items = self.JKG[arraykey][s:f]
            items = batch_json[arraykey][s:f]

            # Associated subschema (nodes or rels)
            subschema = self.JKG_Schema['properties'][arraykey]

            # Validate the chunk against the subschema.
            validation_futures.append(executor.submit(self._validate_items_against_schema, items, subschema))
            chunk_ranges.append((s, f))
            # Advance chunk.
            s = f

        # Collect unique validation errors and deduplicate across all parallel processes.
        sample_validation_errors = set()

        # Update progress as validations complete.
        with tqdm(total=num_chunks, desc=f"Validated chunks", unit=" chunks") as pbar:
            for future, (chunk_s, chunk_f) in zip(as_completed(validation_futures), chunk_ranges):
                sample_validation_errors.update(future.result())
                #pbar.set_postfix_str(f"{chunk_s} to {chunk_f}")
                pbar.update(1)

        for v in validation_futures:
            sample_validation_errors.update(v.result())

        self._write_validation_errors(validation_errors=sample_validation_errors)

    def _validate_json_against_schema(self):

        """
        Validates the JKG JSON file against the JKG schema.

        """
        self.clog.print_and_logger_info("Validating JKG JSON file against the JKG schema.")

        if self.parallel:
            self.clog.print_and_logger_info('Using parallel processing on batched files.')
            # Validate the JSON via parallel processing by schema domain.
            self._validate_batched_json_files()

        else:
            # Validate against the top level schema.
            # This will both take a very long time against a large JSON.
            self.clog.print_and_logger_info('Using single processing on entire JKG JSON file.')
            self._validate_entire()






