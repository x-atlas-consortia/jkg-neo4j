"""
jkg_import.py
Jkgencompare class that compares the edges in a JKGEN edge file with
relationships in a JKG neo4j instance.

The source of new nodes and rels objects is a set of files in
JKG Edde/Node (JkGEN) format.

"""

import os
from pathlib import Path


# Common configuration
from .configfile import ConfigFile

# Centralized application logging
from .centrallog import CentralLog

# Neo4j manager
from .neo4japp import Neo4jApp

class JkgenCompare:

    def __init__(self, cfg: ConfigFile, clog: CentralLog):
        """
        :param cfg: the common config file object
        :param clog: the central logging object
        """

        # Application log
        self.clog = clog
        # Configuration file
        self.cfg = cfg

        # Get the path to the JKGEN source files.
        self.jkgen_path = cfg.get('jkgen_path')
        self.jkgen_sab_path = Path(os.path.join(self.jkgen_path,'UBERON'))
        if not self.jkgen_sab_path.exists():
            self.clog.logger.error('JKGEN path does not exist')
            exit(1)

        # Check for JKGEN path.
        if not self.jkgen_sab_path.is_dir():
            self.clog.logger.error(f'{self.jkgen_sab_path} is not a directory')
            exit(1)

        # Compare the JKGEN files against the JKG instance of neo4j.
        self._compare_jkgen_to_neo4j()

    def _compare_jkgen_to_neo4j(self):
        """
        Compares the edges in a JKG edge file with the specific instance
        of a JKG neo4j instance.

        """

        print('Comparing edges in JKG neo4j...')
        # Connect to Dockerized neo4j instance.
        neo4japp = Neo4jApp(cfg=self.cfg, clog=self.clog)

