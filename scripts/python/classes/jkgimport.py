"""
Class that imports into a Dockerized neo4j instance a set of "batch JKG JSON" files.
The "batch JKG JSON" files were extracted from a JSON file that conforms to the
JKG schema.

"""

import os
from pathlib import Path


# Common configuration
from .configfile import ConfigFile

# Centralized application logging
from .centrallog import CentralLog

# Neo4j manager
from .neo4japp import Neo4jApp

class JkgImport:

    def __init__(self, cfg: ConfigFile, clog: CentralLog):
        """
        :param cfg: the common config file object
        :param clog: the central logging object
        """

        # Application log
        self.clog = clog
        # Configuration file
        self.cfg = cfg

        # Whether to import rels and coderels.
        # This is primarily used to debug Java Out of Memory Errors (OOMEs) related
        # to import. If false, then the script will perform a partial import of
        # just nodes, so that neo4j-admin server memory-recommendation has a database
        # for which to make recommendations.
        self.import_rels = cfg.get('import_rels').lower()=='true'

        if not self.import_rels:
            self.clog.print_and_logger_warning('This import will not include relationships (rels and coderels).')
            self.clog.print_and_logger_warning('To enable import of relationships, set import_rels to true in container.cfg')

        # Get the path to the JKG JSON source file.
        self.jkg_json_dir = cfg.get('jkg_json_dir')
        batch_dir = Path(os.path.join(self.jkg_json_dir,'batch'))
        if not batch_dir.exists():
            self.clog.logger.error('JKG Batch Directory does not exist')
            exit(1)

        # Check for batch files.
        if not batch_dir.is_dir():
            self.clog.logger.error(f'{batch_dir} is not a directory')
            exit(1)

        # Import batch files.
        self._import_batch_files()

    def _import_batch_files(self):
        """
        Imports a set of batch JKG JSON files into a neo4j instance.

        """

        # Connect to Dockerized neo4j instance.
        neo4japp = Neo4jApp(cfg=self.cfg, clog=self.clog)


        # neo4j error: trying to create a constraint that exists already
        ignore_errors = ['Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists']

        # Create constraints on files to import.
        neo4japp.create_constraints(ignore_errors=ignore_errors)

        # Import batch files.
        neo4japp.execute_batched_write_query(type='node')

        if self.import_rels:
            neo4japp.execute_batched_write_query(type='rel')
            neo4japp.execute_batched_write_query(type='coderel')
