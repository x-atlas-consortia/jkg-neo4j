"""
batch_jkg_json.py
Divides a JSON file that conforms to the JKG Schema into a set of smaller
JSON files.

Each file contains a single array of nodes of the same type:
- nodes
- rels (relationships between concepts)
- coderels (relationships between concepts and codes)

A single batch file will contain up to a number of nodes specified in
configuration--e.g., 1 million

"""
import sys
import os
import contextlib

# Common configuration file
from classes.configfile import ConfigFile
# Batching object
from classes.jkgbatch import JKGBatch
# Central logging object
from classes.centrallog import CentralLog

def main():

    # Get configuration information.
    # Assume that the common config file is in the application directory parent.
    cfgfile = os.path.join(os.getcwd(), 'container.cfg')
    cfgobj = ConfigFile(filename=cfgfile)

    # Set up central logging.
    log_dir = cfgobj.config.get('log_dir')
    log_file = 'batch_jkg.log'
    clog = CentralLog(log_dir=log_dir, log_file=log_file)
    clog.print_and_logger_info('********')
    clog.print_and_logger_error('BATCH JKG JSON Script')
    clog.print_and_logger_error('*******')

    # Get the path to the JKG JSON source file.
    jkg_json_dir =  cfgobj.config.get('jkg_json_dir')
    jkg_json_file=cfgobj.config.get('jkg_json_file')

    jkg_batch_size = cfgobj.config.get('jkg_batch_size')

    # Process the JKG JSON file.
    jkgbatch = JKGBatch(jkg_json_dir=jkg_json_dir,
                        jkg_json_file=jkg_json_file,
                        jkg_batch_size=jkg_batch_size,
                        clog = clog)


if __name__ == "__main__":
    main()