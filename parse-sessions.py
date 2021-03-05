import logging
from argparse import ArgumentParser
from pathlib import Path
import re
from datetime import date
from babel.dates import format_date
from lxml import etree
from nltk.tokenize import word_tokenize


class SessionType:
    """Encodes the values for session types.
    """
    Ordinary = 's'
    Extraordinary = 'se'
    Joint = 'sc'
    JointSolemn = 'scs'
    JointVisit = 'scv'


class XmlElements:
    titleStmt = '{http://www.tei-c.org/ns/1.0}titleStmt'
    title = '{http://www.tei-c.org/ns/1.0}title'
    meeting = '{http://www.tei-c.org/ns/1.0}meeting'
    u = '{http://www.tei-c.org/ns/1.0}u'
    div = '{http://www.tei-c.org/ns/1.0}div'
    extent = '{http://www.tei-c.org/ns/1.0}extent'
    measure = '{http://www.tei-c.org/ns/1.0}measure'
    date = '{http://www.tei-c.org/ns/1.0}date'
    bibl = '{http://www.tei-c.org/ns/1.0}bibl'
    setting = '{http://www.tei-c.org/ns/1.0}setting'
    tagUsage = '{http://www.tei-c.org/ns/1.0}tagUsage'
    text = '{http://www.tei-c.org/ns/1.0}text'
    body = '{http://www.tei-c.org/ns/1.0}body'
    head = '{http://www.tei-c.org/ns/1.0}head'
    note = '{http://www.tei-c.org/ns/1.0}note'
    seg = '{http://www.tei-c.org/ns/1.0}seg'
    kinesic = '{http://www.tei-c.org/ns/1.0}kinesic'
    desc = '{http://www.tei-c.org/ns/1.0}desc'
    gap = '{http://www.tei-c.org/ns/1.0}gap'


class XmlAttributes:
    xml_id = '{http://www.w3.org/XML/1998/namespace}id'
    lang = '{http://www.w3.org/XML/1998/namespace}lang'
    element_type = 'type'
    meeting_n = 'n'
    unit = 'unit'
    quantity = 'quantity'
    when = 'when'
    gi = 'gi'
    occurs = 'occurs'


class Resources:
    SessionTitleRo = "Corpus parlamentar român ParlaMint-RO, ședința Camerei Deputaților din {}"
    SessionSubtitleRo = "Stenograma ședinței Camerei Deputaților din România din {}"
    SessionTitleEn = "Romanian parliamentary corpus ParlaMint-RO, Regular Session, Chamber of Deputies, {}"
    SessionSubtitleEn = "Minutes of the session of the Chamber of Deputies of Romania, {}"
    NumSpeechesRo = "{} discursuri"
    NumSpeechesEn = "{} speeches"
    NumWordsRo = "{} cuvinte"
    NumWordsEn = "{} words"
    Heading = "ROMÂNIA CAMERA DEPUTAȚILOR"
    SessionHeading = "Ședinta Camerei Deputaților din {}"
    ToC = "SUMAR"


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


class SessionXmlBuilder:
    """Class responsible for building the XML file with the transcript of a session.
    """
    def __init__(self,
                 input_file,
                 template_file,
                 output_directory,
                 output_file_prefix='ParlaMint-RO'):
        """Creates a new instance of SessionXmlBuilder class.

        Parameters
        ----------
        input_file: str, required
            The path to the HTML file containing the session transcription.
        template_file: str, required
            The path to the file containing the XML template of the output.
        output_directory: str, required
            The path to the output directory.
        output_file_prefix: str, optional
            The prefix of the output file name. Default is `ParlaMint-RO`.
        """
        self.parser = SessionParser(input_file)
        self.output_directory = output_directory
        self.output_file_prefix = output_file_prefix
        self.element_tree = etree.parse(template_file)
        self.xml = self.element_tree.getroot()
        for div in self.xml.iterdescendants(XmlElements.div):
            if div.get(XmlAttributes.element_type) == "debateSection":
                self.debate_section = div

    def write_to_file(self, file_name=None):
        """Writes the XML session to a file given by file_name or session id.

        Parameters
        ----------
        file_name: str, optional
            The name of the output file. Default is the session id.
        """
        if not file_name:
            file_name = "{}.xml".format(self._build_session_id())
        file_name = Path(self.output_directory, file_name)
        self.element_tree.write(str(file_name),
                                pretty_print=True,
                                encoding='utf-8',
                                xml_declaration=True)

    def build_session_xml(self):
        """Builds the session XML from its transcription.
        """
        self.session_date = self.parser.parse_session_date()
        self.session_type = self.parser.parse_session_type()

        self._set_session_id()
        self._set_session_title()
        self._set_meeting_info()
        self._set_session_date()

        self._set_session_heading()

        self._set_session_stats()
        self._set_tag_usage()

        logging.debug(
            etree.tostring(self.element_tree,
                           pretty_print=True,
                           encoding='utf-8',
                           xml_declaration=True))

    def _set_session_heading(self):
        """Adds the head elements to session description.

        """
        head = etree.SubElement(self.debate_section, XmlElements.head)
        head.text = Resources.Heading
        session_head = etree.SubElement(self.debate_section, XmlElements.head)
        session_head.set(XmlAttributes.element_type, "session")
        session_head.text = Resources.SessionHeading.format(
            format_date(self.session_date, "d MMMM yyyy"))

        summary = self.parser.parse_session_summary()
        if len(summary) > 0:
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "editorial")
            note.text = Resources.ToC
        for summary_line in self.parser.parse_session_summary():
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "summary")
            note.text = summary_line.strip()
        heading = self.parser.parse_session_heading()
        if heading is not None:
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "editorial")
            note.text = heading

    def _set_tag_usage(self):
        """Updates the values for tagUsage elements.
        """
        name_map = {
            "text": XmlElements.text,
            "body": XmlElements.body,
            "div": XmlElements.div,
            "head": XmlElements.head,
            "note": XmlElements.note,
            "u": XmlElements.u,
            "seg": XmlElements.seg,
            "kinesic": XmlElements.kinesic,
            "desc": XmlElements.desc,
            "gap": XmlElements.gap
        }
        for tag_usage in self.xml.iterdescendants(tag=XmlElements.tagUsage):
            tag_name = name_map[tag_usage.get(XmlAttributes.gi)]
            num_occurences = self._get_num_occurences(tag_name)
            tag_usage.set(XmlAttributes.occurs, str(num_occurences))

    def _get_num_occurences(self, tag):
        """Computes the number of occurences for the specified tag.

        Parameters
        ----------
        tag: str
            The tag for which to compute number of occurences.

        Returns
        -------
        num_occurences: int
            The number of times the tag is present in the document.
        """
        tags = self.xml.iterdescendants(tag=tag)
        num_occurences = len([t for t in tags])
        return num_occurences

    def _set_session_date(self):
        """Updates the session date in the XML file.
        """
        for date in self.xml.iterdescendants(tag=XmlElements.date):
            parent_tag = date.getparent().tag
            if parent_tag == XmlElements.setting or parent_tag == XmlElements.bibl:
                date.set(XmlAttributes.when,
                         format_date(self.session_date, "yyyy-MM-dd"))
                date.text = format_date(self.session_date, "dd.MM.yyyy")

    def _set_session_stats(self):
        """Updates the session statistics of the extent element.

        """
        num_speeches = self._get_num_speeches()
        num_words = self._get_num_words()
        for m in self.xml.iterdescendants(tag=XmlElements.measure):
            if m.getparent().tag != XmlElements.extent:
                continue
            lang = m.get(XmlAttributes.lang)
            unit = m.get(XmlAttributes.unit)

            qty = num_speeches if unit == 'speeches' else num_words
            m.set(XmlAttributes.quantity, str(qty))
            if unit == 'speeches':
                txt = Resources.NumSpeechesRo if lang == 'ro' else Resources.NumSpeechesEn
            else:
                txt = Resources.NumWordsRo if lang == 'ro' else Resources.NumWordsEn
            m.text = txt.format(qty)

    def _get_num_words(self):
        """Computes the number of words from the session transcription.

        Returns
        -------
        num_words: int
            The number of words in the transcription.
        """
        text = "".join(self.debate_section.itertext())
        num_words = len(word_tokenize(text))
        return num_words

    def _get_num_speeches(self):
        """Computes the number of speeches (a.k.a. utterances).

        Returns
        -------
        num_speeches: int
            The number of speeches in the transcription.
        """
        speeches = [s for s in self.xml.iterdescendants(tag=XmlElements.u)]
        num_speeches = len(speeches)
        return num_speeches

    def _set_meeting_info(self):
        """Sets the contents of the meeting element.

        """
        meeting_n = format_date(self.session_date, "yyyyMMdd")
        for meeting in self.xml.iterdescendants(tag=XmlElements.meeting):
            meeting.set(XmlAttributes.meeting_n, meeting_n)

    def _set_session_title(self):
        """Sets the contents of th title elements.
        """
        ro_date = format_date(self.session_date, "d MMMM yyyy", locale="ro")
        en_date = format_date(self.session_date, "MMMM d yyyy", locale="en")

        for elem in self.xml.iterdescendants(tag=XmlElements.title):
            if elem.getparent().tag != XmlElements.titleStmt:
                continue

            title_type = elem.get(XmlAttributes.element_type)
            lang = elem.get(XmlAttributes.lang)
            if title_type == 'main' and lang == 'ro':
                elem.text = Resources.SessionTitleRo.format(ro_date)

            if title_type == 'main' and lang == 'en':
                elem.text = Resources.SessionTitleEn.format(en_date)

            if title_type == 'sub' and lang == 'ro':
                elem.text = Resources.SessionSubtitleRo.format(ro_date)

            if title_type == 'sub' and lang == 'en':
                elem.text = Resources.SessionSubtitleEn.format(en_date)

    def _set_session_id(self):
        """Sets the id of the TEI element.
        """
        session_id = self._build_session_id()
        self.xml.set(XmlAttributes.xml_id, session_id)

    def _build_session_id(self):
        """Builds the session id from the date and file prefix.

        Returns
        -------
        session_id: str
            The id of the session.
        """
        return "-".join([
            self.output_file_prefix,
            format_date(self.session_date, "yyyy-MM-dd"), "CD"
        ])


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
