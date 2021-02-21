import logging
from argparse import ArgumentParser
from pathlib import Path


def iter_files(directory, file_type='html'):
    """Recursively iterates over the files of the specified type in the given directory.

    Parameters
    ----------
    directory: str, required
        The directory to iterate.
    file_type: str, optional
        The type (extension) of the files to iterate over.
        Default is 'html'.
    """
    root_path = Path(directory)
    for p in root_path.glob('**/*.{}'.format(file_type)):
        print(str(p))
        yield p


def parse_arguments(args):
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
