#!/usr/bin/env python

import logging
import argparse
from lexicalanalysis import CorpusIterator
from xmlbuilder import parse_xml_file, save_xml, XmlAttributes, XmlElements
from itertools import chain


def load_component(file_name):
    """Loads the XML from component file specified by `file_name`.

    Parameters
    ----------
    file_name: str, required
        The path of the file to load.

    Returns
    (xml, component): tuple of (ElementTree, Element)
        The element tree and the root element.
    """
    xml = parse_xml_file(file_name)
    component = xml.getroot()
    return xml, component


def fix_corresp_attribute(args):
    """Replaces the value of `corresp` attribute with provided value.
    """
    logging.info("Replacing the value of corresp attributes.")
    corpus_iterator = CorpusIterator(args.corpus_dir, args.root_file)
    files = chain(corpus_iterator.iter_corpus_files(),
                  corpus_iterator.iter_annotated_files())
    for file_path in files:
        file_name = str(file_path)
        logging.info(
            "Replacing the value of corresp attribute in file {}.".format(
                file_name))
        xml, component = load_component(file_name)
        meeting = next(component.iterdescendants(tag=XmlElements.meeting))
        meeting.set(XmlAttributes.corresp, args.value)
        save_xml(xml, file_name)


def fix_top_level_ids(args):
    """Fixes the top-level ids of the annotated files.
    """
    logging.info("Fixing top-level ids of annotated files.")
    corpus_iterator = CorpusIterator(args.corpus_dir, args.root_file)
    for file_path in corpus_iterator.iter_annotated_files():
        file_name = str(file_path)
        logging.info("Fixing top-level id for component {}.".format(file_name))
        xml, component = load_component(file_name)
        component_id = component.get(XmlAttributes.xml_id)
        component.set(XmlAttributes.xml_id, "{}.ana".format(component_id))
        save_xml(xml, file_name)

    file_name = str(corpus_iterator.annotated_corpus_root_file)
    logging.info("Fixing top-level id for root file {}.".format(file_name))
    xml, corpus = load_component(file_name)
    corpus_id = corpus.get(XmlAttributes.xml_id)
    corpus.set(XmlAttributes.xml_id, "{}.ana".format(corpus_id))
    save_xml(xml, file_name)


def add_title_tag_to_file(file_name, tag):
    """Adds the specified tag to the title of the specified file.

    Parameters
    ----------
    file_name: str, required
        The path of the file to load.
    tag: str, required
        The tag to add to the file.
    """
    logging.info("Adding tag {} to file {}.".format(tag, file_name))
    xml, component = load_component(file_name)
    titleStm = next(component.iterdescendants(tag=XmlElements.titleStmt))
    for title in titleStm.iterdescendants(tag=XmlElements.title):
        if title.get(XmlAttributes.type_) != 'main':
            continue
        if tag not in title.text:
            title.text = "{} {}".format(title.text, tag)
    save_xml(xml, file_name)


def add_title_tags(args):
    """Iterates over corpus files and adds tags to their titles.
    """
    logging.info("Adding title tags to corpus files.")
    corpus_iterator = CorpusIterator(args.corpus_dir, args.root_file)
    # Add tag to unannotated files
    add_title_tag_to_file(str(corpus_iterator.root_file), "[ParlaMint]")
    for file_path in corpus_iterator.iter_corpus_files():
        file_name = str(file_path)
        add_title_tag_to_file(file_name, "[ParlaMint]")
    # Add tag to annotated files
    add_title_tag_to_file(str(corpus_iterator.annotated_corpus_root_file),
                          "[ParlaMint.ana]")
    for file_path in corpus_iterator.iter_annotated_files():
        file_name = str(file_path)
        add_title_tag_to_file(file_name, "[ParlaMint.ana]")


def remove_empty_segments_from_file(file_name):
    """Removes the empty segments from the specified file.

    Parameters
    ----------
    file_name: str, required
        The path of the file from which to remove empty segments.
    """
    xml, component = load_component(file_name)

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


def add_corpus_iterator_args(parser):
    parser.add_argument(
        '--corpus-dir',
        help="Path to the directory containing corpus. Default is ./output",
        default='./output')
    parser.add_argument(
        '--root-file',
        help="The name of the corpus root file. Default is ParlaMint-RO.xml",
        default="ParlaMint-RO.xml")


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
    add_corpus_iterator_args(remove_segments)

    add_tags = subparsers.add_parser(
        'add-tags',
        help=
        "Adds the [ParlaMint] and [ParlaMint.ana] tags to the corpus files.")
    add_tags.set_defaults(func=add_title_tags)
    add_corpus_iterator_args(add_tags)

    fix_tli = subparsers.add_parser(
        'fix-tli', help="Fixes the top-level ids of the annotated files.")
    fix_tli.set_defaults(func=fix_top_level_ids)
    add_corpus_iterator_args(fix_tli)

    parser = subparsers.add_parser(
        'replace-corresp',
        help="Replaces the value of corresp attribute of the meeting element.")
    parser.set_defaults(func=fix_corresp_attribute)
    add_corpus_iterator_args(parser)
    parser.add_argument(
        '--value',
        help="The value to replace with. Default is '#parla.lower'.",
        default='#parla.lower')
    return root_parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=getattr(logging, args.log_level.upper()))
    args.func(args)
    logging.info("That's all folks!")
