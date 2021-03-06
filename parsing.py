import logging
from pathlib import Path
import re
from datetime import date
from babel.dates import format_date
from lxml import etree
from nltk.tokenize import word_tokenize
from common import SessionType
from common import StringFormatter


def get_element_text(element):
    return ''.join(element.itertext())


class Segment:
    """Represents a segment of a  session.
    """
    def __init__(self, paragraph):
        self.paragraph = paragraph
        self.children = list(self.paragraph)
        self.full_text = get_element_text(self.paragraph)

    @property
    def is_speaker(self):
        """Returns true if the segment is a speaker segment.
        """
        match = re.match(r'(domnul|doamna)\s+[^:]+:', self.full_text,
                         re.IGNORECASE | re.MULTILINE)
        return match is not None

    @property
    def has_note(self):
        """Returns true if the current segment contains a note.
        """
        for child in self.paragraph:
            if child.tag == 'i':
                if len(get_element_text(child)) > 0:
                    return True
        return False

    def get_speaker(self):
        """Returns the speaker name if the current segment is a speaker.

        Returns
        -------
        speaker: str
            The speaker name if current segment is a speaker; otherwise None.
        """
        if not self.is_speaker:
            return None
        return re.sub(r'domnul|doamna|(\(.+\)*):', '', self.full_text, 0,
                      re.MULTILINE | re.IGNORECASE)

    def get_text(self):
        """Returns the text of the current segment.

        Returns
        -------
        text: str
            The text of the segment.
        """
        return get_element_text(self.paragraph)

    def get_note_text(self):
        """Returns the editorial note text.

        Returns
        -------
        text: str
            The text of the note.
        """
        for child in self.paragraph:
            if child.tag == 'i':
                return get_element_text(child)
        return None


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
        logging.debug("In SessionParser. HTML root is:\n{}".format(
            etree.tostring(self.html_root, method='html', pretty_print=True)))

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
            line = get_element_text(cols[1])
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
            text = get_element_text(para)
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
            text = get_element_text(para)
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
            text = self.formatter.normalize(get_element_text(para))
            if 'ședința a început la ora' in text.lower():
                self.current_node = para
                return text
        logging.error(
            "Could not parse session start time for file [{}].".format(
                self.file_name))
        return None

    def parse_session_chairmen(self):
        """Parses the segment about who presides the session.

        Returns
        -------
        chairmen_seg: str
            The segment containing info about who presides the session.
        """
        if self.current_node is None:
            logging.error(
                'Current node not set in file [{}]. Cannot parse chairmen segment.'
                .format(self.file_name))
            return None

        self.current_node = self.current_node.getnext()
        text = get_element_text(self.current_node)
        return text

    def parse_session_segments(self):
        """Parses the segments that form the body of the session.

        Returns
        -------
        segments: iterable of Segment
            The segments that form the body of the session.
        """
        if self.current_node is None:
            logging.error(
                'Current node not set in file [{}]. Cannot parse session body.'
                .format(self.file_name))
            return []
        segments = []
        while self.current_node is not None:
            self.current_node = self.current_node.getnext()
            if (self.current_node
                    is not None) and (self.current_node.getnext() is not None):
                segments.append(Segment(self.current_node))
        return segments

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

    def _parse_html(self, html_file):
        parser = etree.HTMLParser()
        tree_root = etree.parse(html_file, parser=parser)
        return tree_root.getroot()
