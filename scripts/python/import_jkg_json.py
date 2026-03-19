"""
import_jkg_json.py
Imports into a Dockerized instance of neo4j a knowledge graph described
in a JSON file that conforms to the JSON Knowledge Graph (JKG) format.

"""
import sys
import os

from classes.configfile import ConfigFile
from classes.jkgbatch import JKGBatch
from classes.centrallog import CentralLog
from classes.jkgvalidate import JKGValidate
from classes.neo4japp import Neo4jApp

def main():

    # Get configuration information.
    # Assume that the common config file is in the application directory parent.
    cfgfile = os.path.join(os.getcwd(), 'container.cfg')
    cfgobj = ConfigFile(filename=cfgfile)

    # Set up central logging.
    log_dir = cfgobj.config.get('log_dir')
    log_file = cfgobj.config.get('log_file')
    clog = CentralLog(log_dir=log_dir, log_file=log_file)
    clog.print_and_logger_info('********')
    clog.print_and_logger_error('import_jkg_json Script')
    clog.print_and_logger_error('*******')

    # Get the path to the JKG JSON source file.
    jkg_json_dir =  cfgobj.config.get('jkg_json_dir')
    jkg_json_file=cfgobj.config.get('jkg_json_file')
    # Obtain the batch size for processing the JKG JSON file.
    jkg_batch_size = cfgobj.config.get('jkg_batch_size')
    jkg_schema_json = cfgobj.config.get('jkg_schema_json')

    jkg_validate = cfgobj.config.get('jkg_validate_schema')
    if jkg_validate=='true':
        # Validate JKG JSON.
        jkgvalidate = JKGValidate(jkg_json_dir=jkg_json_dir,
                                  jkg_json_file=jkg_json_file,
                                  jkg_schema_json=jkg_schema_json,
                                  clog=clog)

    # Process the JKG JSON file.
    #jkgbatch = JKGBatch(jkg_json_dir=jkg_json_dir,
                        #jkg_json_file=jkg_json_file,
                        #jkg_batch_size=jkg_batch_size,
                        #clog = clog)




    # Connect to the neo4j instance.

    # Create indexes and constraints in the graph database.
    # Import the divided source files into the graph database.

if __name__ == "__main__":
    main()