#!/usr/bin/env python

import logging
import argparse
from lexicalanalysis import CorpusIterator
from xmlbuilder import parse_xml_file, save_xml, XmlElements


def remove_empty_segments_from_file(file_name):
    """Removes the empty segments from the specified file.

    Parameters
    ----------
    file_name: str, required
        The path of the file from which to remove empty segments.
    """
    xml = parse_xml_file(file_name)
    component = xml.getroot()
    segments = [
        seg for seg in component.iterdescendants(tag=XmlElements.seg)
        if len(seg) == 0
    ]

    if len(segments) == 0:
        logging.info(
            "File {} does not contain empty segments.".format(file_name))
    return

    logging.info("Removing empty segments from {}.".format(file_name))
    for seg in segments:
        parent = seg.getparent()
        parent.remove(seg)
    save_xml(xml, file_name)


def remove_empty_segments(args):
    """Removes empty segments from corpus component files.
    """
    logging.info("Removing empty segments from corpus.")
    corpus_iterator = CorpusIterator(args.corpus_dir, args.root_file)
    for file_path in corpus_iterator.iter_annotated_files():
        file_name = str(file_path)
        remove_empty_segments_from_file(file_name)
        file_name = corpus_iterator.get_component_file_name(file_path)
        remove_empty_segments_from_file(str(file_name))


def parse_arguments():
    root_parser = argparse.ArgumentParser(
        description='Apply corrections to corpus')
    root_parser.add_argument(
        '-l',
        '--log-level',
        help="The level of details to print when running.",
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
    subparsers = root_parser.add_subparsers()
    remove_segments = subparsers.add_parser(
        'remove-empty-segments',
        help="Removes the empty segments from corpus component files.")
    remove_segments.set_defaults(func=remove_empty_segments)
    remove_segments.add_argument(
        '--corpus-dir',
        help="Path to the directory containing corpus. Default is ./output",
        default='./output')
    remove_segments.add_argument(
        '--root-file',
        help="The name of the corpus root file. Default is ParlaMint-RO.xml",
        default="ParlaMint-RO.xml")
    return root_parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=getattr(logging, args.log_level.upper()))
    args.func(args)
    logging.info("That's all folks!")
