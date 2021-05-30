from common import Resources
from xmlbuilder import RootXmlBuilder
import logging
import argparse
import pandas as pd
import numpy as np


def run(args):
    logging.info("Building root file for the corpus.")
    logging.info("Reading deputy info from {}.".format(args.deputy_info_file))
    deputy_info = pd.read_csv(args.deputy_info_file)
    logging.info("Reading organizations from {}.".format(
        args.organizations_file))
    organizations = pd.read_csv(args.organizations_file)
    organizations = list(organizations.organization)

    builder = RootXmlBuilder(args.template_file, deputy_info, organizations)
    builder.build_corpus_root(args.corpus_dir)
    logging.info("That's all folks!")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build TEI corpus root file.')
    parser.add_argument(
        '--deputy-info-file',
        help=
        "The CSV file containing deputy names, gender, and link to profile picture.",
        default='./deputy-info.csv')
    parser.add_argument('--organizations-file',
                        help="The CSV file containing organization names.",
                        default='./organizations.csv')
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
