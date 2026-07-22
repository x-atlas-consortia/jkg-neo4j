"""
The Neo4App class represents a connection to a JKG neo4j instance.

ASSUMPTIONS:
1. Connect string information is in a config file named container.cfg, located in the
   application path.
2. The neo4j instance is running locally, such as in the Docker container built
   with the Shell scripts in the ubkg-neo4j repo.

"""

import os
import sys
from pathlib import Path
import time
from tqdm import tqdm

# Common configuration
from .configfile import ConfigFile

# Centralized application logging
from .centrallog import CentralLog

import neo4j

class Neo4jApp:

    def __init__(self,cfg: ConfigFile,  clog: CentralLog):

        # Read information from common config file.

        self.cfg = cfg
        self.clog = clog

        # Get the batch directory, which is in the import volume.
        self.batch_dir = Path(os.path.join(os.getcwd(),'import',self.cfg.get('jkg_json_dir'),'batch'))

        neo4j_pasword = self.cfg.get('neo4j_password')
        bolt_port = self.cfg.get('bolt_port')

        # Connect to the specified UBKG instance.
        uri = f'bolt://localhost:{bolt_port}'
        auth = ("neo4j", neo4j_pasword)

        self.driver = neo4j.GraphDatabase.driver(uri, auth=auth,
                                                 connection_acquisition_timeout=600,
                                                 connection_timeout=600,
                                                 max_transaction_retry_time=600)

        # Get the base of URLs to pass to apoc.loadjson to load the batched
        # JKG JSON files.
        self.import_url_base = self.cfg.get('import_url_base')

    def close(self):
        self.driver.close()

    def _getquerycypher(self, cypherfile:str) -> str:
        # Opens an external file to obtain a query Cypher.

        fpath = os.path.join(os.getcwd(), 'python','cypher',cypherfile)
        f = open(fpath, "r")
        query = f.read()
        f.close()
        return query

    def _indexes_are_populating(self) -> str:
        """
        Determines whether any indexes are still populating.

        Returns:
            True - at least one index is populating.

        """
        query = "SHOW INDEXES YIELD state, populationPercent WHERE state <> 'FAILED' " \
                "AND populationPercent <100 RETURN COUNT(populationPercent) AS number_populating"
        with self.driver.session() as session:
            recds: neo4j.Result = session.run(query)
            for record in recds:
                return record['number_populating']

    def execute_batched_write_query(self, type: str) -> None:
        """
        Executes a set of write queries for all batch files of a certain type
        in the batch directory.
        :param type: type of batch files to process

        """
        if type == 'node':
            query = self._getquerycypher('import_nodes.cypher')
        elif type == 'rel':
            query = self._getquerycypher('import_rels.cypher')
        else:
            query = self._getquerycypher('import_coderels.cypher')

        files = sorted([
            f for f in self.batch_dir.iterdir()
            if f.is_file() and f.name.startswith(f'JKG_Batch_{type}') and f.name.endswith('.json')
        ])

        for filepath in tqdm(files, desc=f'Importing {type} files', unit=' files'):
            # Build the url property of the call to apoc.loadjson.
            file = f'{self.import_url_base}{filepath.name}'
            self._execute_write_query_with_params(
                query=query,
                params={'file': file}
                )

    def _execute_write_query(self, cypherfile: str, ignore_errors: list[str] = None):
        """
        Executes a write query based on a cypher file.
        :param cypherfile: cypher file to execute
        :param ignore_errors: list of errors to ignore
        """

        query = self._getquerycypher(cypherfile)
        self.clog.print_and_logger_info(f'Executing: {cypherfile}')
        self._execute_write_query_with_params(query=query, params={}, ignore_errors=ignore_errors)

    def _execute_write_query_with_params(self, query: str, params: dict, ignore_errors: list[str] = None):
        """
        Executes a single statement that writes to the database.
        :param query: Cypher query string
        :param params: Dictionary of neo4j parameters
        :param ignore_errors: list of errors to ignore

        Assumption: query is a Cypher command that writes to the database--e.g., CREATE INDEX; DELETE; etc.

        """

        try:
            with self.driver.session() as session:
                session.run(query, **params)
        except neo4j.exceptions.ClientError as e:
            if ignore_errors and e.code in ignore_errors:
                pass
            else:
                self.clog.print_and_logger_error(f'Error: {e.message}')
                raise

        return


    def create_constraints(self, ignore_errors: list[str] = None):
        """
        Creates constraints using neo4j
        :param ignore_errors: list of errors to ignore
        """

        self._execute_write_query(cypherfile='create_constraint_source.cypher', ignore_errors=ignore_errors)
        self._execute_write_query(cypherfile='create_constraint_term.cypher', ignore_errors=ignore_errors)
        self._execute_write_query(cypherfile='create_constraint_concept.cypher', ignore_errors=ignore_errors)
        self._execute_write_query(cypherfile='create_constraint_rel_label.cypher', ignore_errors=ignore_errors)
        self._execute_write_query(cypherfile='create_constraint_node_label.cypher', ignore_errors=ignore_errors)

        self._wait_for_constraints()

    def _wait_for_constraints(self, expected_count=5, timeout=60):

        """
        Waits until all constraints come online.
        :param expected_count: number of constraints to wait on
        :param timeout: timeout in seconds
        """

        start = time.time()
        while time.time() - start < timeout:
            query = "SHOW CONSTRAINTS YIELD name RETURN count(*) AS count"
            with self.driver.session() as session:
                result = session.run(query)
                count = result.single()["count"]
                if count >= expected_count:
                    print(f"All {count} constraints online")
                    return
                print(f"Waiting... {count}/{expected_count} constraints online")
                time.sleep(2)

        raise TimeoutError("Constraints did not come online in time")

    def create_relationship_indexes(self):

        """
        Creates relationship indexes.
        """

        self.clog.print_and_logger_info(f'Creating relationship indexes')

        # Create a relationship index on the SAB property.
        self._execute_write_query(cypherfile='create_r_sab_index.cypher')

        # Create a relationship index on the codeid property.
        self._execute_write_query(cypherfile='create_r_codeid_index.cypher')

        while int(self._indexes_are_populating()) > 0:
            print(f'{self._indexes_are_populating()} indexes are still populating...')
            time.sleep(5)

        print('All relationship indexes are complete.')

