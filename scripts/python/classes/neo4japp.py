"""
The Neo4App class represents a connection to a JKG neo4j instance.

ASSUMPTIONS:
1. Connect string information is in a config file named container.cfg, located in the
   application path.
2. The neo4j instance is running locally, such as in the Docker container built
   with the Shell scripts in the ubkg-neo4j repo.

"""

import os
import time

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

        neo4j_pasword = self.cfg.get('neo4j_password')
        bolt_port = self.cfg.get('bolt_port')

        # Connect to the specified UBKG instance.
        uri = f'bolt://localhost:{bolt_port}'
        auth = ("neo4j", neo4j_pasword)

        self.driver = neo4j.GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def _indexes_are_populating(self) -> bool:
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
                return record['number_populating'] > 0

    def execute_write_query(self, query: str):
        """
        Executes a single statement that writes to the database.
        :param query: The query to execute.

        Assumption: query is a Cypher command that writes to the database--e.g., CREATE INDEX; DELETE; etc.

        """

        # Enforce synchronous index creation.
        while self._indexes_are_populating():
            # sys.stderr.write('At least one index is still populating. Waiting 1 second...\n')
            time.sleep(1)

        # Transaction management is not necessary for the known use cases, so just use session.run.
        with self.driver.session() as session:
            session.run(query)

        return



