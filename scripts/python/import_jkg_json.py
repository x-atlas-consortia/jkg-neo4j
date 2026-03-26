"""
import_jkg_json.py
Imports a set of batch JKG JSON files into a neo4j instance.

Batch JKG JSON files are extracted (via the batch_jkg_json tool)
from a JKG JSON file that conforms to the JKG Schema.

Each batch file conforms to the JKG schema, and contains a single
non-empty array of nodes of the same type:
- nodes
- rels (relationships between concepts)
- coderels (relationships between concepts and codes)

Although all three arrays will be in the batch file, only one will have values.

A single batch file will contain up to a number of nodes specified in
configuration--e.g., 1 million

"""

import os

# Common configuration file
from classes.configfile import ConfigFile
# Import object
from classes.jkgimport import JkgImport

# Central logging object
from classes.centrallog import CentralLog

def main():

    # Get configuration information.
    # Assume that the common config file is in the application directory parent.
    cfgfile = os.path.join(os.getcwd(), 'container.cfg')
    cfgobj = ConfigFile(filename=cfgfile)

    # Set up central logging.
    log_dir = cfgobj.config.get('log_dir')
    log_file = 'import_jkg_json.log'
    clog = CentralLog(log_dir=log_dir, log_file=log_file)
    clog.print_and_logger_info('********')
    clog.print_and_logger_error('import JKG JSON Script')
    clog.print_and_logger_error('*******')

    # Get the path to the JKG JSON source file.
    jkg_json_dir =  cfgobj.config.get('jkg_json_dir')

    # Import the batch files.
    jkgimport = JkgImport(clog=clog, cfg=cfgobj)

if __name__ == "__main__":
    main()