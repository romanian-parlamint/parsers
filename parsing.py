import logging
from pathlib import Path
import re
from datetime import date
from babel.dates import format_date
from lxml import etree
from nltk.tokenize import word_tokenize
from common import SessionType
from common import StringFormatter
from common import Resources
from collections import deque
from common import get_element_text


def parse_organization_name(organization_name, separator='-'):
    """Splits the organization name into an acronym and the full name.

    Parameters
    ----------
    organization_name: str, required
        The organization name.
    separator: str, optional
        The separator string that is used to split name from acronym.
        Default is '-'.

    Returns
    -------
    (name, acronym): tuple of str
        The name and the acronym (if available) of the organization.
    """
    name, acronym = [], []
    for part in organization_name.split(separator):
        part = part.strip()
        if part.isupper():
            acronym.append(part)
        else:
            name.append(part)
    return '-'.join(name).strip(), '-'.join(acronym).strip()


class Segment:
    """Represents a segment of a  session."""

    def __init__(self, paragraph):
        """Create a new instance of Segment class.

        Parameters
        ----------
        paragraph: etree.Element, required
            The paragraph element to parse into a segment.
        """
        self.paragraph = paragraph
        self.children = list(self.paragraph)
        self.full_text = get_element_text(self.paragraph)

    @property
    def is_speaker(self):
        """Return true if the segment is a speaker segment."""
        match = re.match(r'(domnul|doamna)\s+[^:]+:', self.full_text,
                         re.IGNORECASE | re.MULTILINE)
        if match is None:
            return False

        # When the chairman is doing the name call in a session
        # this can trigger a false positive for is_speaker
        lower_text = self.full_text.lower()
        if 'prezent' in lower_text or 'absent' in lower_text:
            return False

        formatter = StringFormatter()
        speaker = self._get_spearker().strip()
        speaker = formatter.normalize(speaker)
        speaker = formatter.to_single_line(speaker)
        speaker = speaker.replace('-', '').replace(':', '')
        name_parts = speaker.split()
        for p in name_parts:
            if not p[0].isupper():
                return False
        return True

    @property
    def has_note(self):
        """Return true if the current segment contains a note."""
        for child in self.paragraph:
            if child.tag == 'i':
                if len(get_element_text(child)) > 0:
                    return True
        return False

    def get_speaker(self):
        """Return the speaker name if the current segment is a speaker.

        Returns
        -------
        speaker: str
            The speaker name if current segment is a speaker; otherwise None.
        """
        if not self.is_speaker:
            return None
        return self._get_spearker()

    def get_text(self):
        """Return the text of the current segment.

        Returns
        -------
        text: str
            The text of the segment.
        """
        text = get_element_text(self.paragraph)
        return re.sub(r'\s\([^)]+\)*', '', text, 0,
                      re.MULTILINE | re.IGNORECASE)

    def get_note_text(self):
        """Return the editorial note text.

        Returns
        -------
        text: str
            The text of the note.
        """
        for child in self.paragraph:
            if child.tag == 'i':
                if self.is_speaker:
                    return get_element_text(child).replace(':', '')
                return get_element_text(child)
        return None

    def _get_spearker(self):
        speaker = re.sub(r'domnul|doamna|(\(.+\)*)?:', '', self.full_text, 0,
                         re.MULTILINE | re.IGNORECASE)
        return speaker


class TableRowSegment:
    """Represents a segment of a  session extracted from a table row.
    """
    def __init__(self, table_row):
        self.table_row = table_row

    @property
    def is_speaker(self):
        """Returns true if the segment is a speaker segment.
        """
        return False

    @property
    def has_note(self):
        """Returns true if the current segment contains a note.
        """
        return False

    def get_speaker(self):
        """Returns the speaker name if the current segment is a speaker.

        Returns
        -------
        speaker: str
            The speaker name if current segment is a speaker; otherwise None.
        """
        return None

    def get_text(self):
        """Returns the text of the current segment.

        Returns
        -------
        text: str
            The text of the segment.
        """
        text = get_element_text(self.table_row)
        return re.sub(r'\s\([^)]+\)*', '', text, 0,
                      re.MULTILINE | re.IGNORECASE)

    def get_note_text(self):
        """Returns the editorial note text.

        Returns
        -------
        text: str
            The text of the note.
        """
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
        self.end_time_segment = None
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
        found = False
        for para in self.html_root.iterdescendants():
            text = self.formatter.normalize(get_element_text(para))
            if '[1]' in text:
                found = True
                break
        if not found:
            logging.error(
                "Could not find anchor point for session heading in file [{}]".
                format(self.file_name))
            return None
        text = text[:text.find('[1]')]
        text = text.replace(Resources.TranscriptSpaced, Resources.Transcript)
        text = text.replace(Resources.Transcript.upper(), Resources.Transcript)
        idx = text.lower().find(Resources.Transcript.lower())
        text = text[idx:]
        text = self.formatter.to_single_line(text)
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
            canonical_text = text.lower()
            for mark in Resources.SessionStartMarks:
                if mark in canonical_text:
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
        p = None
        self.current_node = None
        for p in self.html_root.iterdescendants(tag='p'):
            s = Segment(p)
            if s.is_speaker:
                break
        segments = []
        self.current_node = p
        segments.append(Segment(self.current_node))
        self.parse_session_end_time()
        while self.current_node is not None:
            self.current_node = self.current_node.getnext()
            if self.current_node == self.end_time_segment:
                self.current_node = None
            if (self.current_node is not None) and (self._contains_table(
                    self.current_node)):
                segments.extend(self._parse_table_segments(self.current_node))
            if (self.current_node is not None):
                segments.append(Segment(self.current_node))
        return segments

    def parse_session_end_time(self):
        """Parses the segment containing end time of the session.

        Returns
        -------
        session_end_time: str
            The segment containing end time of the session.
        """
        if self.end_time_segment is not None:
            text = self.formatter.normalize(
                get_element_text(self.end_time_segment))
            return text

        # Take at most 5 elements from the end of the HTML tree
        # and check if any of them match the end session mark.
        segments = deque(self.html_root.iterdescendants(tag='p'), maxlen=5)
        para = segments.pop()
        while para is not None:
            text = self.formatter.normalize(get_element_text(para))
            if Resources.SessionEndMark in text.lower():
                self.end_time_segment = para
                return text
            para = segments.pop()

        logging.error("Could not parse session end time for file [{}].".format(
            self.file_name))
        return None

    def _parse_table_segments(self, elem):
        """Converts the rows of the table from within the specified element to segments.

        Parameters
        ----------
        element: etree element
            The element containing table rows.

        Returns
        -------
        segments: iterable of TableRowSegment
            The collection of parsed segments.
        """
        if not self._contains_table(elem):
            return []

        return [TableRowSegment(tr) for tr in elem.iterdescendants(tag='tr')]

    def _contains_table(self, elem):
        """Checks if the current element contains a table.

        Parameters
        ----------
        elem: etree element
            The element to check.

        Returns
        -------
        True if element contains table; False otherwise.
        """
        if elem.tag == 'table':
            return True
        table = [elem for elem in elem.iterdescendants(tag='table')]
        return len(table) > 0

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
