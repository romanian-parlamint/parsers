import logging
from argparse import ArgumentParser
from pathlib import Path
import re
from datetime import date
from babel.dates import format_date
from lxml import etree
from nltk.tokenize import word_tokenize
from xmlbuilder import SessionXmlBuilder


def iter_files(directory, file_type='html', include_files=None):
    """Recursively iterates over the files of the specified type in the given directory.

    Parameters
    ----------
    directory: str, required
        The directory to iterate.
    file_type: str, optional
        The type (extension) of the files to iterate over.
        Default is 'html'.
    include_files: str, optional
        A pattern to filter files. Default is `None` which means include all.

    Returns
    -------
    file_path: generator of pathlib.Path
        The generator that returns the path of each file.
    """
    root_path = Path(directory)
    for file_path in root_path.glob('**/*.{}'.format(file_type)):
        if not include_files:
            yield file_path

        match = re.search(include_files, str(file_path), re.IGNORECASE)
        if match:
            yield file_path


def run(args):
    total, processed, failed = 0, 0, 0
    for f in iter_files(args.input_directory,
                        include_files=args.include_files):
        input_file = str(f)
        total = total + 1
        logging.info("Building session XML from [{}].".format(input_file))
        builder = SessionXmlBuilder(input_file, args.session_template_xml,
                                    args.output_directory)
        try:
            builder.build_session_xml()
            builder.write_to_file(group_by_year=args.group_by_year,
                                  use_xmllint=not args.no_xmllint)
            processed = processed + 1
        except:
            failed = failed + 1
            logging.error(
                "Failed to build XML transcription for file [{}].".format(
                    input_file))
    logging.info("Processed: {}/{} files.".format(processed, total))
    logging.info("Failed: {}/{} files.".format(failed, total))
    logging.info("That's all folks!")


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument(
        '-i',
        '--input-directory',
        help=
        "The root directory containing session transcripts. Default value is './corpus'.",
        default='./corpus')
    parser.add_argument(
        '--include-files',
        help='A regex pattern to filter which files will be included.',
        default='20[0-9]{2}')
    parser.add_argument(
        '--session-template-xml',
        help="The file containing the XML template of a section.",
        default='./session-template.xml')
    parser.add_argument(
        '-o',
        '--output-directory',
        help=
        "The directory where to output XML files. Default value is './output'.",
        default='./output')
    parser.add_argument(
        '--group-by-year',
        help='Specifies whether to group output files by year.',
        action='store_true')
    parser.add_argument('--no-xmllint',
                        help='Do not call xmllint to format output files.',
                        action='store_true')
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
