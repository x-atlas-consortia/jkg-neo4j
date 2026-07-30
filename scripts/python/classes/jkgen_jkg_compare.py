"""
jkg_import.py
Jkgencompare class that compares the edges in a JKGEN edge file with
relationships in a JKG neo4j instance.

The source of new nodes and rels objects is a set of files in
JKG Edde/Node (JkGEN) format.

"""

import os
from pathlib import Path
import ast


# Common configuration
from .configfile import ConfigFile

# Centralized application logging
from .centrallog import CentralLog

# Neo4j manager
from .neo4japp import Neo4jApp

import pandas as pd
import neo4j
import tqdm

class JkgenCompare:

    def __init__(self, cfg: ConfigFile, clog: CentralLog, sabs:list[str]):
        """
        :param cfg: the common config file object
        :param clog: the central logging object
        :param sabs: list of SABs
        """

        # Application log
        self.clog = clog
        # Configuration file
        self.cfg = cfg
        # SAB list
        self.sabs = sabs

        # Get the path to the JKGEN source files.
        self.jkgen_path = cfg.get('jkgen_path')
        if not os.path.exists(self.jkgen_path):
            self.clog.logger.error(f'JKGEN path {self.jkgen_path} does not exist')
            exit(1)

        # Connect to the JKG neo4j instance
        self.neo4japp = Neo4jApp(cfg=self.cfg, clog=self.clog)

        # Compare the JKGEN files against the JKG instance of neo4j.
        for sab in self.sabs:
            self._compare_jkgen_to_neo4j(sab=sab)

    def _compare_edges(self, jkgen_sab_path: Path):
        """
        Compares the edges in a JKGEN edge file against the JKG neo4j.
        :param jkgen_sab_path: path to SAB's JKGEN edge file.
        """
        self.clog.logger.debug(f'Loading edge file in {jkgen_sab_path}...')
        edgefile = os.path.join(jkgen_sab_path,'jkg_edge.tsv')
        dfedge = pd.read_csv(edgefile,sep='\t')

        for index, row in tqdm.tqdm(dfedge.iterrows(), total=dfedge.shape[0]):
            # Get JKGEN triplet.
            subject = row['subject']
            predicate = row['predicate']
            object = row['object']

            # Build Cypher query string.
            querytxt = f"MATCH (t:Term)<-[r:CODE{{codeid:'{subject}',tty:'PT'}}]-(c:Concept)-[r2:{predicate}]->(c2:Concept)-[r3:CODE {{tty:'PT',codeid:'{object}'}}]->(t2:Term) RETURN COUNT(*) AS count"

            with self.neo4japp.driver.session() as session:
                result = session.run(querytxt)
                count = result.single()["count"]
                if count>0:
                    in_ubkg = "Y"
                else:
                    in_ubkg = "N"
                dfedge.loc[index, 'in_ubkg'] = in_ubkg

            outfile = os.path.join(jkgen_sab_path,'jkg_edge_comparison.tsv')
            dfedge.to_csv(outfile,sep='\t',index=False)


    def _compare_nodes(self, jkgen_sab_path: Path):
        """
        Compares the nodes in a JKGEN node file against the JKG neo4j.
        :param jkgen_sab_path: path to SAB's JKGEN node file.
        """

        # The node_cuis.csv file aggregates cui assignments. Use this as
        # a proxy for the node file.
        self.clog.logger.debug(f'Loading node_cuis file in {jkgen_sab_path}...')
        nodefile = os.path.join(jkgen_sab_path,'node_cuis.tsv')
        dfnode = pd.read_csv(nodefile, sep='\t')

        for index, row in tqdm.tqdm(dfnode.iterrows(), total=dfnode.shape[0]):

            # Get node id and set of cuis.
            node_id = row['node_id']
            jkgen_cuis = set(ast.literal_eval(row['cuis']))

            # Build Cypher query string to obtain list of linked CUIs.
            querytxt = f"MATCH (t:Term)<-[r:CODE{{codeid:'{node_id}'}}]-(c:Concept) RETURN DISTINCT c.id AS cui"
            jkg_cuis = []
            with self.neo4japp.driver.session() as session:
                result = session.run(querytxt)
                for record in result:
                    jkg_cuis.append(record['cui'])
                if jkgen_cuis == set(jkgen_cuis):
                    in_ubkg = "Y"
                else:
                    in_ubkg = "N"
                dfnode.loc[index, 'in_ubkg'] = in_ubkg

            outfile = os.path.join(jkgen_sab_path,'jkg_node_comparison.tsv')
            dfnode[['node_label','cuis','in_ubkg']].to_csv(outfile,sep='\t',index=False)

    def _compare_jkgen_to_neo4j(self, sab: str):
        """
        Compares the JKGEN files for a SAB with the specified instance
        of a JKG neo4j instance.
        :param sab: the SAB for the JKGEN files

        """

        self.clog.print_and_logger_info(f'Comparing JKGEN for {sab} against JKG neo4j...')

        # Connect to Dockerized neo4j instance.
        neo4japp = Neo4jApp(cfg=self.cfg, clog=self.clog)

        jkgen_sab_path = Path(os.path.join(self.jkgen_path, sab))
        print('Path: ', jkgen_sab_path)

        # Compare edges in JKGEN edge file.
        self._compare_edges(jkgen_sab_path=jkgen_sab_path)

        # Compare nodes in JKGEN node file.
        self._compare_nodes(jkgen_sab_path=jkgen_sab_path)


