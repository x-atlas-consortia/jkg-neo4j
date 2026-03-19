"""
Class that splits a large file in JSON Knowledge Graph format into sets of the
following types of files:
- nodes
- rels other than CODE
- CODE rels

Each file in a set will contain a number of nodes up to a value specified at
instantiation.
"""

import ijson
import json
import os
import shutil
from tqdm import tqdm
import io

from .centrallog import CentralLog

class JKGBatch:

    def _mkdir_clean(self, path: str):
        """
        Create a directory at `path`.
        - If it already exists: delete it entirely and recreate it.
        - If it does not exist: create it fresh.
        """
        if os.path.exists(path):
            self.clog.print_and_logger_info('Deleting existing path: ' + path)
            shutil.rmtree(path)  # Delete folder and ALL contents recursively

        self.clog.print_and_logger_info('Creating new path: ' + path)
        os.makedirs(path)  # Always recreate

    def _split_nodes(self):
        """
        Splits the nodes array in the JKG JSON source to a set of smaller
        JSON files, each containing up to the batch size number of elements.
        """
        self.clog.print_and_logger_info('Splitting nodes into smaller JSON files')

        json_source = os.path.join(self.jkg_json_dir, self.jkg_json_file)
        with open(json_source, 'rb') as f:
            i = 0
            batch_num = 0
            batch_progress = None

            # Stream through the nodes array.
            for item in ijson.items(f, 'nodes.item'):
                if (i % self.jkg_batch_size) == 0:

                    # Close the previous batch's progress bar, if any.
                    if batch_progress is not None:
                        batch_progress.close()

                    # Start a new batch file.
                    batch_file = 'JKG_Batch' + 'n' + str(int(i / self.jkg_batch_size)).zfill(4) + '_JKG.json'
                    batch_path = os.path.join(self.jkg_json_dir,'batch',batch_file)
                    file = open(batch_path, "w")
                    file.write('{"nodes":[\n')

                    # Start a new per-batch progress bar.
                    batch_num += 1
                    batch_progress = tqdm(
                        total=self.jkg_batch_size,
                        desc=f'Batch {batch_num}',
                        unit='node',
                        leave=True,
                    )

                else:
                    # New line
                    file.write('\n,')

                # Write the node object to output.
                file.write(json.dumps(item))
                batch_progress.update(1)

                if (i % self.jkg_batch_size) == (self.jkg_batch_size - 1):
                    # Close the current batch output file.
                    file.write('\n],"rels":[]}')
                    file.close()
                i += 1

            # Close the final progress bar.
            if batch_progress is not None:
                batch_progress.close()

            self.clog.print_and_logger_info('Finishing nodes')
            if (i % self.jkg_batch_size) != 0:
                # Close the current batch output file.
                file.write('\n],"rels":[]}')
                file.close()

    def _close_and_remove_dangling_file(self, rfile: io.TextIOWrapper):

        """
        Removes rels files that contain no rels items.
        :param filename:
        """
        rfile.write('\n]}')
        rfile.close()

        if os.path.getsize(rfile.name) == self.dangling_file_size:
            os.remove(rfile.name)

    def _start_rel_batch_file(self, prefix: str, ibatch: int) -> io.TextIOWrapper:

        batch_file_name = 'JKG_Batch' + prefix + str(int(ibatch / self.jkg_batch_size)).zfill(4) + '_JKG.json'
        batch_path = os.path.join(self.jkg_json_dir, 'batch', batch_file_name)

        batch_file = open(batch_path, "w")
        batch_file.write('{"nodes":[],"rels":[\n')
        return batch_file

    def _split_rels(self):
        """
            Splits the rels array in the JKG JSON source to two sets of smaller
            JSON files, each containing up to the batch size number of elements.
        """

        self.clog.print_and_logger_info('Splitting rels into smaller JSON files')

        json_source = os.path.join(self.jkg_json_dir, self.jkg_json_file)

        with open(json_source, 'rb') as f:
            i = 0

            # Boolean flags:
            firstR = False # first rel batch?
            firstCR = False # first CODE rel batch?

            batch_num = 0
            batch_progress = None

            # Stream through the rels array.
            for item in ijson.items(f, 'rels.item'):

                if i % self.jkg_batch_size == 0:

                    # Close the previous batch's progress bar, if any.
                    if batch_progress is not None:
                        batch_progress.close()

                    # Start new batch files for rels and CODE rels.
                    rfile = self._start_rel_batch_file(prefix='r', ibatch=i)
                    crfile = self._start_rel_batch_file(prefix='cr', ibatch=i)

                    firstCR = True
                    firstR = True

                    # Start a new per-batch progress bar.
                    batch_num += 1
                    batch_progress = tqdm(
                        total=self.jkg_batch_size,
                        desc=f'Batch {batch_num}',
                        unit='rel',
                        leave=True,
                    )

                # Distribute rel items between non-CODE and CODE rels files.
                if item['label'] == 'CODE':
                    if not firstCR:
                        crfile.write('\n,')
                    crfile.write(json.dumps(item))
                    firstCR = False
                else:
                    if not firstR:
                        rfile.write('\n,')
                    rfile.write(json.dumps(item))
                    firstR = False

                batch_progress.update(1)

                if (i % self.jkg_batch_size) == self.jkg_batch_size-1:
                    # Close the current batch output files.
                    # Remove any dangling output files.
                    self._close_and_remove_dangling_file(rfile=rfile)
                    self._close_and_remove_dangling_file(rfile=crfile)

                i += 1

            # Close the final progress bar.
            if batch_progress is not None:
                batch_progress.close()

            self.clog.print_and_logger_info('Finishing rels')

            if (i % self.jkg_batch_size) != 0:

                # Close the current batch output files.
                # Remove any dangling output files.
                self._close_and_remove_dangling_file(rfile=rfile)
                self._close_and_remove_dangling_file(rfile=crfile)


    def _split_json(self):

        self.clog.print_and_logger_error(f'Processing JKG JSON file:  {self.jkg_json_file}')
        batch_path = os.path.join(self.jkg_json_dir, 'batch')
        # Clear any prior batched files
        self._mkdir_clean(batch_path)

        self.clog.print_and_logger_info(f'Working in batches of {self.jkg_batch_size}.')
        self._split_nodes()
        self._split_rels()


    def __init__(self, jkg_json_dir: str, jkg_json_file: str,
                 jkg_batch_size: int, clog: CentralLog):
        """

        :param jkg_json_dir: path to the JKG JSON file
        :param jkg_json_file: filename of the JKG JSON file
        :param jkg_batch_size: size of each batch--i.e., the maximum number of
               objects that should be in each split file
        :param clog: the central logging object
        """
        self.jkg_json_dir = jkg_json_dir
        self.jkg_json_file = jkg_json_file
        self.jkg_batch_size = int(jkg_batch_size)
        self.clog = clog

        self.dangling_file_size = 24

        self._split_json()

