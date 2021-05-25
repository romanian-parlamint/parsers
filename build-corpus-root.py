from common import Resources
from xmlbuilder import RootXmlBuilder
import logging
import argparse
import pandas as pd
import numpy as np


def run(args):
    logging.info("Building root file for the corpus.")
    logging.info("Reading affiliations from {}.".format(
        args.deputy_affiliations_file))
    affiliations = pd.read_csv(args.deputy_affiliations_file)
    logging.info("Removing empty rows from the affiliations file.")
    affiliations.dropna(subset=['first_name', 'last_name'], inplace=True)
    builder = RootXmlBuilder(args.template_file, affiliations)
    builder.build_corpus_root(args.corpus_dir)
    logging.info("That's all folks!")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build TEI corpus root file.')
    parser.add_argument(
        '--deputy-affiliations-file',
        help=
        "Path to the CSV file containing affiliation records for the deputies.",
        default='./deputy-affiliations.csv')
    parser.add_argument('--template-file',
                        help="Path to the corpus root template file.",
                        default='./corpus-root-template.xml')
    parser.add_argument('--corpus-dir',
                        help="Path to the directory containing corpus.",
                        default='./output')
    parser.add_argument(
        '-l',
        '--log-level',
        help="The level of details to print when running.",
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=getattr(logging, args.log_level.upper()))
    run(args)
