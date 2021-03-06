import logging
from pathlib import Path
import re
from datetime import date
from babel.dates import format_date
from lxml import etree
from nltk.tokenize import word_tokenize
from common import SessionType
from common import StringFormatter


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
        self.formatter = StringFormatter()
        self.file_name = str(html_file) if isinstance(html_file,
                                                      Path) else html_file
        self.html_root = self._parse_html(html_file)

    def parse_session_date(self):
        """Parses the session date from the name of the session file.

        Returns
        -------
        session_date: datetime.date
            The session date.
        """
        session_date, _ = self._parse_date_and_type()
        return session_date

    def parse_session_type(self):
        """Parses the session type from the name of the session file.

        Returns
        -------
        session_type: str
            The type of the session.
        """
        _, session_type = self._parse_date_and_type()
        return session_type

    def parse_session_summary(self):
        """Parses the session summary table.

        Returns
        -------
        summary_lines: list of str
            The list fo summary lines.
        """
        try:
            self.summary_table = next(
                self.html_root.iterdescendants(tag='table'))
        except StopIteration:
            logging.error('Could not find summary table for file [{}].'.format(
                self.file_name))
            return []
        summary_lines = []
        for row in self.summary_table.iterdescendants(tag="tr"):
            cols = list(row)
            line = self._get_element_text(cols[1])
            summary_lines.append(line)
        return summary_lines

    def parse_session_heading(self):
        """Parses the session heading.

        Returns
        -------
        heading: str
            The heading line.
        """
        heading_elem = None
        found = False
        for para in self.html_root.iterdescendants(tag='p'):
            text = self._get_element_text(para)
            if '[1]' in text:
                found = True
                break
        if not found:
            logging.error(
                "Could not find anchor point for session heading in file [{}]".
                format(self.file_name))
            return None
        found = False
        while (para is not None) and (para.tag != 'table') and (not found):
            para = para.getprevious()
            text = self._get_element_text(para)
            found = 'stenograma' in text.lower()
        if not found:
            logging.error(
                "Could not parse session heading in file [{}].".format(
                    self.file_name))
            return None
        return text

    def parse_session_start_time(self):
        """Parses the segment containing start time of the session.

        Returns
        -------
        session_start_time: str
            The segment containing session start time or None.
        """
        for para in self.html_root.iterdescendants(tag='p'):
            text = self.formatter.normalize(self._get_element_text(para))
            if 'ședința a început la ora' in text.lower():
                self.current_node = para
                return text
        logging.error(
            "Could not parse session start time for file [{}].".format(
                self.file_name))
        return None

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
