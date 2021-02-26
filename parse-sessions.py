import logging
from argparse import ArgumentParser
from pathlib import Path
import re
from datetime import date
import dateparser
from lxml import etree


class SessionType:
    """Encodes the values for session types.
    """
    Ordinary = 's'
    Extraordinary = 'se'
    Joint = 'sc'
    JointSolemn = 'scs'
    JointVisit = 'scv'


class SessionParser:
    """Class responsible for parsing a session html file.
    """
    def __init__(self, html_file):
        """Creates a new instance of the SessionParser class.

        Parameters
        ----------
        html_file: str or pathlib.Path
            The HTML file containing session transcription.
        """

        self.file_name = str(html_file) if isinstance(html_file,
                                                      Path) else html_file
        self.html_root = self._parse_html(html_file)

    def parse_session_date(self):
        dt, _ = self._parse_date_and_type()
        return dt

    def _parse_date_and_type(self):
        """Parses the session date and type from file path.

        Returns
        -------
        (session_date, session_type): tuple of (datetime.date, str)
            The session date and its type.
        """
        msg = 'Parsing session date and type from file name [{}]'.format(
            self.file_name)
        logging.info(msg)
        match = re.search(
            r"/(?P<year>\d{4})/(\d{2}/)?(?P<type>[a-z]{1,3})-?(?P<day>\d{2})(-|_)(?P<month>\d{2})",
            self.file_name)
        if not match:
            msg = "Could not parse session date and type from file [{}].".format(
                self.file_name)
            logging.error(msg)
            return (None, None)

        session_date = date(int(match.group('year')),
                            int(match.group('month')), int(match.group('day')))
        session_type = match.group('type')

        return (session_date, session_type)

    def _get_element_text(self, element):
        return ''.join(element.itertext())

    def _parse_html(self, html_file):
        parser = etree.HTMLParser()
        tree_root = etree.parse(html_file, parser=parser)
        return tree_root.getroot()


def iter_files(directory, file_type='html'):
    """Recursively iterates over the files of the specified type in the given directory.

    Parameters
    ----------
    directory: str, required
        The directory to iterate.
    file_type: str, optional
        The type (extension) of the files to iterate over.
        Default is 'html'.

    Returns
    -------
    file_path: generator of pathlib.Path
        The generator that returns the path of each file.
    """
    root_path = Path(directory)
    for file_path in root_path.glob('**/*.{}'.format(file_type)):
        yield file_path


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument(
        '-i',
        '--input-directory',
        help=
        "The root directory containing session transcripts. Default value is './corpus'.",
        default='./corpus')
    parser.add_argument(
        '-o',
        '--output-directory',
        help=
        "The directory where to output XML files. Default value is './output'.",
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
    logging.info("That's all folks!")
