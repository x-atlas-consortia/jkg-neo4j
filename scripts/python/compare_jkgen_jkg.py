"""
compare_jkgen_edges_to_jkg_rels.py
Script that compares the triplets in a JKGEN edge file against a neo4j
instance of UBKG JKG.

Tasks:
1. Reads a set of "edge/node files"--files in JKG Edge/Node (JKGEN)
   format generated from a translation of data from a non-UMLS data
   source--e.g., an OWL file
2. For each triplet in the JKGEN edge file, builds and executes a
   Cypher query against the specified UBKG-JKG instance.
3. Reports on whether the triplet has a corresponding relationship in
   the UBKG-JKG.

"""

import os

# Common configuration file
from classes.configfile import ConfigFile
# Import object
from classes.jkgen_jkg_compare import JkgenCompare

# Central logging object
from classes.centrallog import CentralLog

import argparse
# argparser
from classes.ubkg_args import RawTextArgumentDefaultsHelpFormatter

def get_args() -> argparse.Namespace:
    """
    Obtains command line arguments.
    :return: parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Compare the JKGEN files of a SAB against a JKG instance',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)

    # Multiple SABs can be ingested as a space-delimited list.
    parser.add_argument('sabs', nargs='*', help='space-delimited list of SABs')

    args = parser.parse_args()

    return args

def main():

    # Get configuration information.
    # Assume that the common config file is in the application directory parent.
    cfgfile = os.path.join(os.getcwd(), 'container.cfg')
    cfgobj = ConfigFile(filename=cfgfile)

    # Get the SABs to compare.
    args = get_args()

    # Set up central logging.
    log_dir = cfgobj.config.get('log_dir')
    log_file = 'compare_jkged_jkg.log'
    clog = CentralLog(log_dir=log_dir, log_file=log_file)
    clog.print_and_logger_info('********')
    clog.print_and_logger_error('Script to compare JKGEN and JKG')
    clog.print_and_logger_error(f'SABs: {",".join(args.sabs)}')

    # Get the path to the JKG JSON source file.
    jkg_json_dir =  cfgobj.config.get('jkg_json_dir')

    # Import the batch files.
    jkgimport = JkgenCompare(clog=clog, cfg=cfgobj, sabs=args.sabs)

if __name__ == "__main__":
    main()