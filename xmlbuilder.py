import logging
from datetime import date
from babel.dates import format_date
import re
from lxml import etree
from common import Resources
from parsing import SessionParser
from nltk.tokenize import word_tokenize
from pathlib import Path
from common import StringFormatter


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
    ana = 'ana'
    who = 'who'


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
        self.formatter = StringFormatter()
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
            file_name = "{}.xml".format(self.id_builder.session_id)
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
        self.id_builder = XmlIdBuilder(self.output_file_prefix,
                                       self.session_date)
        self._set_session_id()
        self._set_session_title()
        self._set_meeting_info()
        self._set_session_date()

        self._build_session_heading()
        self._build_session_body()

        self._set_session_stats()
        self._set_tag_usage()

        logging.debug(
            etree.tostring(self.element_tree,
                           pretty_print=True,
                           encoding='utf-8',
                           xml_declaration=True))

    def _build_session_body(self):
        """Adds the session segments to the session description.
        """
        is_first = True
        for segment in self.parser.parse_session_segments():
            if segment.is_speaker:
                note = etree.SubElement(self.debate_section, XmlElements.note)
                note.set(XmlAttributes.element_type, "speaker")
                note.text = self.formatter.to_single_line(segment.get_text())
                utterance = etree.SubElement(self.debate_section,
                                             XmlElements.u)
                if is_first:
                    chairman = self.formatter.to_single_line(
                        segment.get_speaker())
                    is_first = False
                speaker = self.formatter.to_single_line(segment.get_speaker())
                utterance.set(XmlAttributes.ana,
                              "#chair" if speaker == chairman else "#regular")
                utterance.set(XmlAttributes.who,
                              self.id_builder.get_speaker_id(speaker))
                utterance.set(XmlAttributes.xml_id,
                              self.id_builder.build_utterance_id())

    def _build_session_heading(self):
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
            note.text = self.formatter.normalize(summary_line)
        heading = self.parser.parse_session_heading()
        if heading is not None:
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "editorial")
            note.text = self.formatter.to_single_line(heading)
        start_time = self.parser.parse_session_start_time()
        if start_time is not None:
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "time")
            note.text = self.formatter.to_single_line(start_time)
        chairmen = self.parser.parse_session_chairmen()
        if chairmen is not None:
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "chairman")
            note.text = self.formatter.to_single_line(chairmen)

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
        self.xml.set(XmlAttributes.xml_id, self.id_builder.session_id)


class XmlIdBuilder:
    """Builds the values for id attributes of XML elements.
    """
    def __init__(self, prefix, session_date):
        """Creates a new instance of XmlIdBuilder.
        """
        self.prefix = prefix
        self.session_date = session_date
        self.root_id = None
        self.utterance_index = 0

    @property
    def session_id(self):
        """Gets the session id.

        Returns
        -------
        session_id: str
            The session id.
        """
        if self.root_id is None:
            self.root_id = self._build_session_id()
        return self.root_id

    def get_speaker_id(self, speaker):
        """Gets the id of the speaker if speaker is a known person or builds new id.

        Returns
        -------
        speaker_id: str
            The id of the speaker.
        """
        return "#{}".format(re.sub(r'\s+', '-', speaker, 0, re.MULTILINE))

    def build_utterance_id(self):
        """Builds the id of the current utterance.

        Returns
        -------
        utterance_id: str
            The id of the current utterance.
        """
        self.utterance_index = self.utterance_index + 1
        return "{}.u{}".format(self.session_id, self.utterance_index)

    def _build_session_id(self):
        """Builds the session id from the date and file prefix.

        Returns
        -------
        session_id: str
            The id of the session.
        """
        self.root_id = "-".join(
            [self.prefix,
             format_date(self.session_date, "yyyy-MM-dd"), "CD"])
        return self.session_id
