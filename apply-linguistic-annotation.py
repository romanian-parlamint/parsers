#!/usr/bin/env python
from lexicalanalysis import CorpusComponentAnnotator, UDPipe
import logging
import argparse
from xmlbuilder import parse_xml_file, XmlAttributes, XmlElements
from pathlib import Path


class CorpusIterator:
    def __init__(self, corpus_dir, root_file):
        """Creates a new instance of CorpusIterator.

        Parameters
        ----------
        corpus_dir : str, required
            The path to the corpus directory.
        root_file : str, required
            The name of the root file in corpus.
        """
        self.corpus_dir = Path(corpus_dir)
        self.corpus_root_file = Path(self.corpus_dir, root_file)
        self.annotated_corpus_root_file = Path(
            self.corpus_dir, "{}.ana.xml".format(self.corpus_root_file.stem))

    @property
    def root_file(self):
        """Gets the root file of the corpus.

        Returns
        -------
        root_file: pathlib.Path
            The path of the root file.
        """
        return self.corpus_root_file

    @property
    def annotated_root_file(self):
        """Gets the annotated root file of the corpus.

        Returns
        -------
        annotated_root_file: pathlib.Path
            The path of the annotated root file.
        """
        return self.annotated_corpus_root_file

    def iter_corpus_files(self, skip_annotated=False):
        """Iterates over corpus files.

        Parameters
        ----------
        skip_annotated: bool, optional
            Specifies whether to iterate over all corpus files or just the ones that are not annotated.
            Default is False which means iterate over all corpus files.

        Returns
        -------
        file_generator: generator of pathlib.Path
            The generator that iterates corpus files one by one.
        """
        annotated_files = set()
        if skip_annotated:
            annotated_files = set([
                self._get_file_name_without_extensions(f)
                for f in self.iter_annotated_files()
            ])

        for file_path in self.corpus_dir.glob("*.xml"):
            if file_path == self.root_file:
                continue
            if ('.ana' not in file_path.suffixes) and (file_path.stem
                                                       not in annotated_files):
                yield file_path

    def iter_annotated_files(self):
        """Iterates over annotated corpus files.

        Returns
        -------
        file_generator: generator of pathlib.Path
            The generator that iterates annotated corpus files one by one.
        """
        for file_path in self.corpus_dir.glob("*.ana.xml"):
            if file_path == self.annotated_root_file:
                continue
            yield file_path

    def _get_file_name_without_extensions(self, file_path):
        """Gets the file name by replacing all extensions with empty strings.

        Parameters
        ----------
        file_path: urllib.Path, required
            The path of the file.

        Returns
        stem: str
            File name without extensions.
        """
        stem = file_path.stem
        for ext in file_path.suffixes:
            stem = stem.replace(ext, '')
        return stem


def main(args):
    iterator = CorpusIterator(args.corpus_dir, args.root_file)
    udpipe = UDPipe()
    for component_file in iterator.iter_corpus_files(
            skip_annotated=args.resume):
        annotator = CorpusComponentAnnotator(component_file, udpipe)
        annotator.apply_annotation()
    for annotated_file in iterator.iter_annotated_files():
        print(str(annotated_file))
    # for each segment:
    # - call UDPipe
    # - replace segment text with sentences and words
    # - add segment text to CoNLL-U string
    # save xml root to component_file.ana.xml
    # save CoNLL-U string to component_file.conllu


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
        '--resume',
        help=
        "Specifies whether to resume annotation or start anew. Default is start anew.",
        action='store_true')
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
