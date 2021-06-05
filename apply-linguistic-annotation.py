#!/usr/bin/env python
from lexicalanalysis import UDPipe
import logging
import argparse


def main(args):
    pass


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Apply linguistic annotations to corpus.')
    parser.add_argument('--corpus-dir',
                        help="Path to the directory containing corpus.",
                        default='./output')
    parser.add_argument(
        '--root-file',
        help="The name of the corpus root file. Default is ParlaMint-RO.xml",
        default="ParlaMint-RO.xml")
    parser.add_argument(
        '--root-file-template',
        help=
        """The path to the template of the root file. It should contain the taxonomy describing UD dependencies.""",
        default="corpus-root-template.ana.xml")
    parser.add_argument('--ud-taxonomy-id',
                        help="The XML id of the UD taxonomy.",
                        default='UD-SYN')
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
    main(args)
