"""
Class that validates a JKG JSON file against the JKG schema.
"""

# Used for file management
import io
import os
import contextlib

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

# Centralized application logging
from .centrallog import CentralLog

# Timer for lazy event process monitoring
from .jkg_timer import JkgTimer

# File reading
from .progressreader import ProgressReader

class JKGValidate:

    def __init__(self, jkg_json_dir: str, jkg_json_file: str,
                 jkg_schema_json: str, jkg_validate_chunk: str,
                 clog: CentralLog):
        """
        :param jkg_json_dir: path to the JKG JSON file
        :param jkg_json_file: filename of the JKG JSON file
        :param jkg_schema_json: filename of the JKG schema JSON file
        :param jkg_validate_chunk: chunk size for subscheme validation
        :param clog: the central logging object
        """

        self.jkg_json_dir = jkg_json_dir
        self.jkg_json_file = jkg_json_file
        self.jkg_json_schema = jkg_schema_json
        self.jkg_validate_chunk = int(jkg_validate_chunk)
        self.clog = clog

        # Parse JKG files.
        self.clog.print_and_logger_warning('Historical estimates are for the UMLS JKG.JSON (4.3 GB).')
        self._parse_jkg_files()

        # Load nodes and rels arrays from JKG JSON into Pandas.
        self._load_nodes_rels_dataframe()
        # Validate node uniqueness.
        self._validate_nodes_for_uniqueness()
        # Validate referential integrity.
        self._validate_referential_integrity()

        # Iteratively validate JSON against schema.
        self._validate_json_against_schema()

    def _parse_jkg_files(self):

        """
        Parse JKG JSON file and JKG schema file.
        """

        self.clog.print_and_logger_warning("The historical time to parse the JKG.JSON is under 6 minutes.")
        self.JKG = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_file)
        self.JKG_Schema = self._load_json(dir=self.jkg_json_dir, filename=self.jkg_json_schema)

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
        self.starts = pd.json_normalize(rels.start)
        jtimer.stop()

        self.clog.print_and_logger_warning("The historical time to normalize rels end is under 2 minutes.")
        jtimer = JkgTimer(display_msg=f"Normalizing rels end")
        self.ends = pd.json_normalize(rels.end)
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

    def _log_issue(self, issue_frame: pd.DataFrame, noerrmsg: str, filename: str):

        """
        Writes missing or duplicate items to a CSV file.
        :param missing_values: DataFrame of missing information.
        :param noerrmsg: message to display in log.
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

    def _format_validation_error(self, error, items: list, s: int) -> str:

        """
        Formats a jsonschema ValidationError into a human-readable message.
        :param error: a jsonschema ValidationError
        :param items: the slice of items being validated
        :param s: start offset of the slice in the full list
        :return: formatted error message string
        """
        path = list(error.absolute_path)
        msg = f'VALIDATION ERROR: {error.message}'

        if path and isinstance(path[0], int):
            offending_item = items[path[0]]
            msg = f'{msg} FOR ITEM: {offending_item}'

        return msg

    def _validate_against_top_level(self):

        # Validate JKG against top level of JKG_Schema.
        jtimer = JkgTimer(display_msg=f"Validating against the top-level JKG schema")

        v = Draft202012Validator(self.JKG_Schema)
        errors = sorted(v.iter_errors(self.JKG), key=lambda e: e.path)

        # Validation errors not printed to terminal.
        for error in errors:
            msg = self._format_validation_error(error=error, items=self.JKG, s=0)
            self.clog.logger.error(msg)

        jtimer.stop()

    def _validate_items_against_subschema(self, items: list, s:int, f:int, subschema: dict) -> set:
        """
        Validates a set of nodes from the JKG JSON against the specified
        schema.
        :param items: a slice of a list of JKG JSON nodes
        :param s: start node identifier
        :param f: finish node identifier
        :param subschema: part of a JSON schema
        :return: set of unique error messages per validation
        """

        v = Draft202012Validator(subschema)
        errors = sorted(v.iter_errors(items), key=lambda e: e.path)
        return {self._format_validation_error(error=error, items=items, s=s) for error in errors}

    def _validate_nodes_against_subschema(self, subschema: dict, nodetype: str):

        """
        Validates a set of nodes from the JKG JSON against the specified schema.
        :param nodetype: type of node - e.g., "nodes", "rels"
        :param subschema: part of a JSON schema

        """

        max_index = len(self.JKG[nodetype]) - 1
        executor = get_reusable_executor(max_workers=10, timeout=3)

        self.clog.print_and_logger_info(f"In each {self.jkg_validate_chunk} {nodetype} up to one invalid entry is flagged.")

        futures = []
        s = 0
        while s < max_index:
            f = min(s + self.jkg_validate_chunk, max_index)
            self.clog.print_and_logger_info(f"Validating {nodetype} {s} to {f}")
            items = self.JKG[nodetype][s:f]
            # Collect errors from this validation chunk.
            futures.append(executor.submit(self._validate_items_against_subschema, items, s, f, subschema))
            # executor.submit(self._validate_items_against_subschema, items, s, f, subschema)
            s = f

        # Collect any validation errors and deduplicate across all chunks
        seen = set()
        for future in futures:
            seen.update(future.result())

        #Validation errors written to log, but not printed to terminal.
        for msg in seen:
            self.clog.logger.error(msg)

    def _validate_json_against_schema(self):

        """
        Validates the JKG JSON file against the JKG schema.

        """
        self.clog.print_and_logger_info("Validating JKG JSON file against the JKG schema.")

        #self._validate_against_top_level()

        # Split JKG schema into nodes and rels subschemata.
        nodes_schema = self.JKG_Schema['properties'].pop('nodes')
        rels_schema = self.JKG_Schema['properties'].pop('rels')

        self._validate_nodes_against_subschema(nodetype='nodes', subschema=nodes_schema)
        self._validate_nodes_against_subschema(nodetype='rels', subschema=rels_schema)




