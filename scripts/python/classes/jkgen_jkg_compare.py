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

    def _compare_edges(self, jkgen_sab_path: Path, sab:str):
        """
        Compares the edges in a JKGEN edge file against the JKG neo4j.
        :param jkgen_sab_path: path to SAB's JKGEN edge file.
        """
        self.clog.print_and_logger_info(f'Loading edge file in {jkgen_sab_path}...')
        edgefile = os.path.join(jkgen_sab_path,'jkg_edge.tsv')
        dfedge = pd.read_csv(edgefile,sep='\t')

        self.clog.print_and_logger_info(f'Loading node_cuis file in {jkgen_sab_path}...')
        nodefile = os.path.join(jkgen_sab_path, 'node_concept_assignments.tsv')
        dfnode = pd.read_csv(nodefile, sep='\t')

        dfedgecui = dfedge.merge(
            dfnode,
            how='left',
            left_on='subject',
            right_on='node_id').rename(columns={'assigned_cui':'subject_cui'})
        dfedgecui = dfedgecui[['subject','subject_cui','predicate','object']]
        dfedgecui = dfedgecui.merge(
            dfnode,
            how='left',
            left_on='object',
            right_on='node_id').rename(columns={'assigned_cui':'object_cui'})
        dfedgecui = dfedgecui[['subject','subject_cui','predicate','object','object_cui']]
        outfile = os.path.join(jkgen_sab_path, 'jkg_edge_cui.tsv')
        dfedgecui.to_csv(outfile, sep='\t', index=False)

        # Query the JKG.
        self.clog.print_and_logger_info(f'Reading rels from JKG...')
        querytxt = f"match (c:Concept)-[r {{sab:'{sab}'}}]->(c2:Concept) RETURN DISTINCT c.id AS subject_cui,type(r) AS predicate, c2.id AS object_cui"

        listrels=[]
        with self.neo4japp.driver.session() as session:
            result = session.run(querytxt)
            records = list(result)
            for record in tqdm.tqdm(records, desc='Building DataFrame of rels', total=len(records)):
                listrels.append({'subject_cui': record['subject_cui'], 'predicate': record['predicate'],
                                 'object_cui': record['object_cui']})
            dfjkgrels = pd.DataFrame(listrels)

        self.clog.print_and_logger_info('Comparing edges...')
        df_jkgen_edge_not_in_jkg = dfedgecui.merge(
            dfjkgrels,
            how='left_anti',
            on=['subject_cui','predicate','object_cui']
        )
        outfile = os.path.join(jkgen_sab_path, 'jkgen_edge_not_in_jkg_rel.tsv')
        df_jkgen_edge_not_in_jkg.to_csv(outfile, sep='\t', index=False)

        df_jkg_rel_not_in_jkgen_edge = dfjkgrels.merge(
            dfedgecui,
            how='left_anti',
            on=['subject_cui', 'predicate', 'object_cui']
        )
        outfile = os.path.join(jkgen_sab_path, 'jkg_rel_not_in_jkgen_edge.tsv')
        df_jkg_rel_not_in_jkgen_edge.to_csv(outfile, sep='\t', index=False)

    def _compare_nodes(self, jkgen_sab_path: Path, sab: str):
        """
        Compares the nodes in a JKGEN node file against the JKG neo4j.
        :param jkgen_sab_path: path to SAB's JKGEN node file.
        """

        # The node_cuis.csv file aggregates cui assignments. Use this as
        # a proxy for the node file.
        self.clog.logger.debug(f'Loading node_cuis file in {jkgen_sab_path}...')
        nodefile = os.path.join(jkgen_sab_path,'node_concept_assignments.tsv')
        df_jkgen_node = pd.read_csv(nodefile, sep='\t')

        self.clog.print_and_logger_info('Querying JKG for nodes information...')
        # Build Cypher query string to obtain list of linked CUIs for each node from the SAB.
        querytxt = f"MATCH (t:Term)<-[r:CODE{{sab:'{sab}'}}]-(c:Concept) RETURN r.codeid AS node_id, COLLECT(DISTINCT c.id) AS cuis"

        listnodes = []
        with self.neo4japp.driver.session() as session:
            result = session.run(querytxt)
            records = list(result)
            for record in tqdm.tqdm(records, desc='Building DataFrame of nodes', total=len(records)):
                listnodes.append({'node_id': record['node_id'], 'cuis': record['cuis']})
            df_jkg_node = pd.DataFrame(listnodes)
        df_node_compare = df_jkgen_node.merge(
            df_jkg_node,
            how='left',
            on='node_id')
        df_node_compare = df_node_compare[['node_id','cuis_x','cuis_y']]

        outfile = os.path.join(jkgen_sab_path, 'node_comparison.tsv')
        df_node_compare.to_csv(outfile, sep='\t', index=False)

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
        self._compare_edges(jkgen_sab_path=jkgen_sab_path, sab=sab)

        # Compare nodes in JKGEN node file.
        self._compare_nodes(jkgen_sab_path=jkgen_sab_path, sab=sab)


