import logging
from argparse import ArgumentParser
from pathlib import Path
import re
from datetime import date


class SessionType:
    """Encodes the values for session types.
    """
    Ordinary = 's'
    Extraordinary = 'se'
    Joint = 'sc'
    JointSolemn = 'scs'
    JointVisit = 'scv'


def parse_session_date_and_type_from_path(file_path):
    """Parses the session date and type from file path.

    Parameters
    ----------
    file_path: str or pathlib.Path, required
        The path of the file containing session transcription.

    Returns
    -------
    (session_date, session_type): tuple of (datetime.date, str)
        The session date and its type.
    """
    if isinstance(file_path, Path):
        file_path = str(file_path)

    logging.info(
        'Parsing session date and type from file name [{}]'.format(file_path))
    match = re.search(
        r"/(?P<year>\d{4})/(?P<month>\d{2})/(?P<type>[a-z]{1,3})(?P<day>\d{2})-(?P=month)",
        file_path)
    if not match:
        logging.error(
            "Could not parse session date and type from file [{}].".format(
                file_path))
        return (None, None)
    session_date = date(int(match.group('year')), int(match.group('month')),
                        int(match.group('day')))
    session_type = match.group('type')

    return (session_date, session_type)


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
        help="The root directory containing session transcripts.",
        required=True)
    parser.add_argument('-o',
                        '--output-directory',
                        help="The directory where to output XML files.",
                        required=True)
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
