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
    log_dir = cfgobj.config.get('log_dir')
    log_file = cfgobj.config.get('log_file')
    clog = CentralLog(log_dir=log_dir, log_file=log_file)
    clog.print_and_logger_info('********')
    clog.print_and_logger_error('validate_jkg_json Script')
    clog.print_and_logger_error('*******')

    # Get the path to the JKG JSON source file.
    jkg_json_dir =  cfgobj.config.get('jkg_json_dir')
    jkg_json_file=cfgobj.config.get('jkg_json_file')
    # Obtain the batch size for processing the JKG JSON file.
    jkg_batch_size = cfgobj.config.get('jkg_batch_size')
    jkg_schema_json = cfgobj.config.get('jkg_schema_json')

    jkg_validate = cfgobj.config.get('jkg_validate_schema')
    if jkg_validate=='true':
        jkg_validate_chunk = cfgobj.config.get('jkg_validate_chunk')
        vlog_file = cfgobj.config.get('validation_error_log_file')
        vlog_path = os.path.join(log_dir, vlog_file)
        # Validate JKG JSON.
        jkgvalidate = JKGValidate(jkg_json_dir=jkg_json_dir,
                                  jkg_json_file=jkg_json_file,
                                  jkg_schema_json=jkg_schema_json,
                                  jkg_validate_chunk=jkg_validate_chunk,
                                  clog=clog)


if __name__ == "__main__":
    main()