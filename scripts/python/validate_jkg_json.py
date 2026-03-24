"""
validate_jkg_json.py
Validates a JSON file in JSON Knowledge Graph (JKG) format against the
JKG schema.

"""
import sys
import os
import contextlib

from classes.configfile import ConfigFile
from classes.centrallog import CentralLog
from classes.jkgvalidate import JKGValidate

def main():

    # Get configuration information.
    # Assume that the common config file is in the application directory parent.
    cfgfile = os.path.join(os.getcwd(), 'container.cfg')
    cfgobj = ConfigFile(filename=cfgfile)

    # Set up central logging.
    log_dir = cfgobj.get('log_dir')
    log_file = 'validate_jkg_json.log'
    clog = CentralLog(log_dir=log_dir, log_file=log_file)
    clog.print_and_logger_info('********')
    clog.print_and_logger_error('VALIDATE JKG JSON Script')
    clog.print_and_logger_error('*******')

    # Validate JKG JSON.
    jkgvalidate = JKGValidate(cfg=cfgobj, clog=clog)


if __name__ == "__main__":
    main()