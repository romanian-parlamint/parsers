import logging
from datetime import date
from babel.dates import format_date
import re
from lxml import etree
from common import Resources
from parsing import parse_organization_name, SessionParser
from nltk.tokenize import word_tokenize
from pathlib import Path
from common import StringFormatter
from common import build_speaker_id, Gender, OrganizationType
import subprocess
from collections import namedtuple
from dateutil import parser


class XmlElements:
    TEI = '{http://www.tei-c.org/ns/1.0}TEI'
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
    idno = '{http://www.tei-c.org/ns/1.0}idno'
    listOrg = '{http://www.tei-c.org/ns/1.0}listOrg'
    org = '{http://www.tei-c.org/ns/1.0}org'
    orgName = '{http://www.tei-c.org/ns/1.0}orgName'
    event = '{http://www.tei-c.org/ns/1.0}event'
    listPerson = '{http://www.tei-c.org/ns/1.0}listPerson'
    person = '{http://www.tei-c.org/ns/1.0}person'
    persName = '{http://www.tei-c.org/ns/1.0}persName'
    forename = '{http://www.tei-c.org/ns/1.0}forename'
    surname = '{http://www.tei-c.org/ns/1.0}surname'
    sex = '{http://www.tei-c.org/ns/1.0}sex'
    affiliation = '{http://www.tei-c.org/ns/1.0}affiliation'
    figure = '{http://www.tei-c.org/ns/1.0}figure'
    graphic = '{http://www.tei-c.org/ns/1.0}graphic'
    s = '{http://www.tei-c.org/ns/1.0}s'
    w = '{http://www.tei-c.org/ns/1.0}w'
    pc = '{http://www.tei-c.org/ns/1.0}pc'
    linkGrp = '{http://www.tei-c.org/ns/1.0}linkGrp'
    link = '{http://www.tei-c.org/ns/1.0}link'


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
    full = 'full'
    role = 'role'
    event_start = 'from'
    event_end = 'to'
    value = 'value'
    url = 'url'
    ref = 'ref'
    role = 'role'
    msd = 'msd'
    pos = 'pos'
    lemma = 'lemma'
    targFunc = 'targFunc'
    type_ = 'type'
    target = 'target'
    corresp = 'corresp'


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
        self.element_tree = parse_xml_file(template_file)
        self.xml = self.element_tree.getroot()
        for div in self.xml.iterdescendants(XmlElements.div):
            if div.get(XmlAttributes.element_type) == "debateSection":
                self.debate_section = div

    def write_to_file(self,
                      file_name=None,
                      group_by_year=False,
                      use_xmllint=False):
        """Writes the XML session to a file given by file_name or session id.

        Parameters
        ----------
        file_name: str, optional
            The name of the output file. Default is the session id.
        group_by_year: boolean, optional
            Specifies whether to group output files into directories by year.
            Default is `False`.
        use_xmllint: boolean, optional
            Specifies whether to use `xmllint` program for formatting the output xml.
            Default is `False`.
        """
        if not file_name:
            file_name = "{}.xml".format(self.id_builder.session_id)
        if group_by_year:
            year = str(self.session_date.year)
            directory = Path(self.output_directory, year)
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
            file_name = Path(directory, file_name)
        else:
            file_name = Path(self.output_directory, file_name)

        file_name = str(file_name)
        save_xml(self.element_tree, file_name, use_xmllint=use_xmllint)

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
        self._set_session_idno()
        self._set_session_date()

        self._build_session_heading()
        self._build_session_body()
        self._build_session_footer()
        self._cleanup_xml()
        self._set_session_stats()
        self._set_tag_usage()

    def _cleanup_xml(self):
        for u in self.debate_section.iterdescendants(tag=XmlElements.u):
            if len(u) == 0:
                self.debate_section.remove(u)
            u.set(XmlAttributes.xml_id, self.id_builder.build_utterance_id())

    def _build_session_footer(self):
        """Adds the end time segment(s) to the session description.
        """
        end_time = self.parser.parse_session_end_time()
        if end_time is not None:
            note = etree.SubElement(self.debate_section, XmlElements.note)
            note.set(XmlAttributes.element_type, "time")
            note.text = self.formatter.to_single_line(end_time)

    def _build_session_body(self):
        """Adds the session segments to the session description.
        """
        is_first = True
        utterance = None
        for segment in self.parser.parse_session_segments():
            text = segment.get_text()
            if len(text) == 0:
                continue
            if segment.is_speaker:
                note = etree.SubElement(self.debate_section, XmlElements.note)
                note.set(XmlAttributes.element_type, "speaker")
                note.text = self.formatter.to_single_line(text)

                if segment.has_note:
                    note = etree.SubElement(self.debate_section,
                                            XmlElements.note)
                    note.set(XmlAttributes.element_type, "editorial")
                    note.text = self.formatter.to_single_line(
                        segment.get_note_text())

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
            else:
                seg = etree.SubElement(utterance, XmlElements.seg)
                seg.set(XmlAttributes.xml_id,
                        self.id_builder.build_segment_id())
                seg.text = self.formatter.to_single_line(text)

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

    def _set_session_idno(self):
        """Updates the vale of `idno` element.
        """
        for idno in self.xml.iterdescendants(tag=XmlElements.idno):
            if idno.get(XmlAttributes.element_type) == 'URI':
                date = format_date(self.session_date, "yyyyMMdd")
                idno.text = "http://www.cdep.ro/pls/steno/steno2015.data?cam=2&dat={}".format(
                    date)

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


def apply_xmllint(file_name):
    """Formats the specified file using xmllint.

    Parameters
    ----------
    file_name: str, required
        The full name of the file to be formatted.
    """
    logging.info("Formatting file [{}] using xmllint.".format(file_name))
    proc = subprocess.Popen(
        ['xmllint', '--format', '--output', file_name, file_name],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)
    proc.wait()


def parse_xml_file(file_name):
    """Parses the specified XML file.

    Parameters
    ----------
    file_name: str, required
        The name of the XML file.

    Returns
    -------
    xml_tree: etree.ElementTree
        The XML tree from the file.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    xml_tree = etree.parse(file_name, parser)
    for element in xml_tree.iter():
        element.tail = None
    return xml_tree


def save_xml(xml, file_name, use_xmllint=True):
    """Saves the provided XML tree to the specified file and optionally applies xmllint.

    Parameters
    ----------
    xml : etree.ElementRoot, required
        The XML tree to save to disk.
    file_name : str, required
        The file where to save the XML.
    use_xmllint: bool, optional
        Specifies whether to apply xmllint or not.
        Default is `True`.
    """
    xml.write(file_name,
              pretty_print=True,
              encoding='utf-8',
              xml_declaration=True)
    if use_xmllint:
        apply_xmllint(file_name)


def add_component_file_to_corpus_root(component_file, corpus_root):
    """Adds the `component_file` to the list of included files in the corpus.

    Parameters
    ----------
    component_file: pathlib.Path, required
        The path of the component file.
    corpus_root: etree.Element, required
        The corpus root element.
    """
    file_name = component_file.name
    logging.info("Addind file {} to included files.".format(file_name))
    # I don't have time to investigate how to do this properly so I'm applying this hack.
    include_element = etree.fromstring(
        '<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="{}"/>'.
        format(file_name))
    corpus_root.append(include_element)


DeputyInfo = namedtuple("DeputyInfo",
                        ['first_name', 'last_name', 'gender', 'image_url'])


class RootXmlBuilder:
    """Builds the corpus root XML file.
    """
    def __init__(self,
                 template_file,
                 deputy_info,
                 organizations,
                 parliament_id="RoParl",
                 id_char_replacements=None):
        """Creates a new instance of RootXmlBuilder.

        Parameters
        ----------
        template_file: str, required
            The path to the template file for corpus root.
        deputy_info: pandas.DataFrame, required
            The data frame containing deputy names, gender, and link to profile picture.
        organizations: iterable of str, required
            The collection of organization names.
        parliament_id: str, optional
            The id of the organization with role='parliament'.
        id_char_replacements: dict of (str, str), optional
            A dict containing the uppercase and lowercase characters that are not valid for id strings and their replacements.
        """
        self.xml_root = parse_xml_file(template_file)
        self.corpus_root = self.xml_root.getroot()
        self.deputy_info = deputy_info
        self.organizations = organizations
        self.id_char_replacements = id_char_replacements if id_char_replacements is not None else {}
        self.name_map = self._build_name_map(self.deputy_info)
        self.male_names = set()
        self.female_names = set()
        self._split_names_by_gender()
        self.parliament_terms = self._parse_terms_list(parliament_id)
        self.existing_persons = {}
        self.person_affiliations = {}
        self.ids_to_replace = {}

    @property
    def id_replacement_list(self):
        """Returns the list of ids to be replaced.
        """
        return [(id_string, canonical_id)
                for id_string, canonical_id in self.ids_to_replace.items()]

    def build_corpus_root(self,
                          corpus_dir,
                          file_name="ParlaMint-RO.xml",
                          apply_postprocessing=True):
        """Builds the corpus root file by aggregating corpus files in corpus_dir.

        Parameters
        ----------
        corpus_dir: str, required
            The path to the directory containing corpus files.
        file_name: str, optional
            The name of the output file. Default is `ParlaMint-RO.xml`.
        apply_postprocessing: bool, optional
            Specifies whether to apply any postprocessing actions like replacing invalid characters in ids.
            Default is True.
        """
        self.corpus_dir = Path(corpus_dir)
        self._build_organizations_list()
        for component_file in self._iter_files(self.corpus_dir, file_name):
            logging.info("Adding file {} to corpus root.".format(
                str(component_file)))
            corpus_component = parse_xml_file(str(component_file)).getroot()
            self._update_tag_usage(corpus_component)
            self._add_or_update_speakers(corpus_component)
            self._add_component_file(component_file)
        self._write_file(file_name)
        logging.info("Finished building root file of the corpus.")
        if apply_postprocessing:
            logging.info("Post-processing is enabled.")
            self._apply_id_correction(self.corpus_dir, file_name)

    def _apply_id_correction(self, corpus_dir, root_file_name):
        """Iterates over the files in corpus directory and replaces the ids containing invalid characters with the normalized ones.

        Parameters
        ----------
        corpus_dir: pathlib.Path, required
            The path of the corpus directory.
        root_file_name: str, required
            The name of the root file of the corpus within `corpus_dir`.
        """
        logging.info("Applying id correction to corpus files.")
        for component_file in self._iter_files(corpus_dir, root_file_name):
            self._correct_ids_in_file(component_file)
        logging.info("Applying id correction to root file.")
        for person in self.corpus_root.iterdescendants(tag=XmlElements.person):
            speaker_id = person.get(XmlAttributes.xml_id)
            if speaker_id in self.ids_to_replace:
                person.set(XmlAttributes.xml_id,
                           self.ids_to_replace[speaker_id])
        logging.info("Saving root file.")
        self._write_file(root_file_name)
        logging.info("Finished applying id correction.")

    def _correct_ids_in_file(self, component_file):
        """Replaces the ids containing invalids values to canonical ones in the specified component file.

        Parameters
        ----------
        component_file: pathlib.Path, required
            The path of the file to replace the ids in.
        """
        file_name = str(component_file)
        logging.info("Correcting the ids in file {}.".format(file_name))
        xml_root = parse_xml_file(file_name)
        corpus_component = xml_root.getroot()
        corrections_applied = False
        for u in corpus_component.iterdescendants(tag=XmlElements.u):
            speaker_id = u.get(XmlAttributes.who).strip('#')
            if speaker_id in self.ids_to_replace:
                cannonical_id = self.ids_to_replace[speaker_id]
                u.set(XmlAttributes.who, "#{}".format(cannonical_id))
                corrections_applied = True
        if corrections_applied:
            logging.info("Saving file {}.".format(file_name))
            save_xml(xml_root, file_name)
        else:
            logging.info(
                "File {} has no ids to be corrected.".format(file_name))

    def _add_component_file(self, component_file):
        """Adds the `component_file` to the list of included files in the corpus.

        Parameters
        ----------
        component_file: pathlib.Path, required
            The path of the component file.
        """
        file_name = Path(component_file)
        add_component_file_to_corpus_root(file_name, self.corpus_root)

    def _add_or_update_speakers(self, corpus_component):
        """Iterates over the speakers from the `corpus_component` and adds them to the list of speakers or updates their affiliation.

        Parameters
        ----------
        corpus_component: etree.ElementTree, required
            The contents of the component file as an XML tree.
        """
        logging.info("Updating speakers.")
        session_date = None
        for date_elem in corpus_component.iterdescendants(
                tag=XmlElements.date):
            if date_elem.getparent().tag == XmlElements.bibl:
                session_date = parser.parse(date_elem.get(XmlAttributes.when))
        if session_date is None:
            logging.error("Could not parse session date.")
        person_list = next(
            self.corpus_root.iterdescendants(tag=XmlElements.listPerson))
        for utterance in corpus_component.iterdescendants(tag=XmlElements.u):
            speaker_id = utterance.get(XmlAttributes.who)
            key = self._build_name_map_key(speaker_id)
            speaker_id = speaker_id.strip('#')
            existing_person = self._find_person_by_id(person_list, speaker_id)
            if key not in self.name_map:
                # This is an unknown person.
                # If a person with the same id does not exist - add it. Otherwise do nothing.
                if existing_person is None:
                    self._add_unknown_speaker(person_list, speaker_id)
            else:
                # This is a known person but it may not have been added to the persons list.
                # If it is not added, add new element.
                if existing_person is None:
                    dep_info = self.name_map[key]
                    existing_person = self._add_person(
                        person_list, speaker_id,
                        dep_info.first_name.split(' '),
                        dep_info.last_name.split(' '), Gender.Male
                        if dep_info.gender == "M" else Gender.Female,
                        dep_info.image_url)
                # This is a known person that has already been added to the person list.
                self._update_speaker_affiliation(existing_person, session_date)

    def _update_speaker_affiliation(self,
                                    speaker,
                                    session_date,
                                    parliament_id="RoParl"):
        """Adds a new affiliation element to the person with the reference to the parliament term if it doesn't exist.

        Parameters
        ----------
        speaker: etree.Element, required
            The `person` element for which to update affiliation.
        session_date: date, required
            The date of the session. It will be used to identify the parliament term.
        parliament_id: str, optional
            The id value of the parliament organization.
        """
        logging.info("Updating speaker affiliation.")
        term = None
        for start_date, end_date, term_id in self.parliament_terms:
            if (start_date <= session_date) and ((end_date is None) or
                                                 (session_date <= end_date)):
                term = (start_date, end_date, term_id)
        if term is None:
            logging.warning("Could not find term for session date {}.".format(
                str(session_date)))
            return
        start_date, end_date, term_id = term
        speaker_id = speaker.get(XmlAttributes.xml_id)
        if self._affiliation_exists(speaker_id, term_id):
            logging.info("Affiliation {}--{} already exists.".format(
                speaker_id, term_id))
            return

        new_affiliation = self._build_affiliation_element(
            start_date, end_date, term_id, parliament_id)
        speaker.append(new_affiliation)
        if speaker_id not in self.person_affiliations:
            self.person_affiliations[speaker_id] = set()
        speaker_affiliations = self.person_affiliations[speaker_id]
        speaker_affiliations.add(term_id)

    def _affiliation_exists(self, speaker_id, term_id):
        """Checks if there is an affiliation element for the specified person, which references the specified term.

        Parameters
        ----------
        speaker_id: str, required
            The id of the person.
        term_id: str, required
            The id of the legislative term.

        Returns
        -------
        True if affiliation element exists; False otherwise.
        """
        if speaker_id not in self.person_affiliations:
            return False
        affiliations = self.person_affiliations[speaker_id]
        return term_id in affiliations

    def _build_affiliation_element(self, start_date, end_date, term_id,
                                   parliament_id):
        """Builds a new affiliation element.

        Parameters
        ----------
        start_date: date, required
            The start date of the affiliation.
        end_date: date, required
            The end date of the affiliation; may be None.
        term_id: str, required
            The id of the legislative term representing the affiliation.
        parliament_id: str, required
            The id of the parliament organization.

        Returns
        -------
        affiliation: etree.Element
            The affiliation element.
        """
        logging.info("Building new affiliation element.")
        affiliation = etree.Element(XmlElements.affiliation)
        affiliation.set(XmlAttributes.event_start,
                        format_date(start_date, "yyyy-MM-dd"))
        if end_date is not None:
            affiliation.set(XmlAttributes.event_end,
                            format_date(end_date, "yyyy-MM-dd"))
        affiliation.set(XmlAttributes.ana, '#{}'.format(term_id))
        affiliation.set(XmlAttributes.ref, '#{}'.format(parliament_id))
        affiliation.set(XmlAttributes.role, 'member')
        return affiliation

    def _find_person_by_id(self, person_list, person_id):
        """Iterates over `person_list` to find the person with the provided id.

        Parameters
        ----------
        person_list: etree.Element, required
            The element containing the list of persons.
        person_id: str, required
            The id of the person to find.

        Returns
        -------
        person: etree.Element
            The person with the specified id if found; None otherwise.
        """
        logging.info("Looking up person with id #{}.".format(person_id))
        if person_id in self.existing_persons:
            logging.info(
                "Person with id #{} already exists.".format(person_id))
            return self.existing_persons[person_id]
        return None

    def _add_person(self,
                    person_list,
                    person_id,
                    first_name,
                    last_name,
                    gender,
                    image_url=None):
        """Adds a new `person` element to the element specified by `person_list` with the provided values.

        Parameters
        ----------
        person_list: etree.Element, required
            The parent element to which to add a new person.
        person_id: str, required
            The id of the new person.
        first_name: iterable of str, required
            The parts of the first name.
        last_name: iterable of str, required
            The parts of the last name.
        gender: str, required
            Male of Female - the gender of the person to be added.
        image_url: str, optional
            The URL of the person image if exists.

        Returns
        -------
        person: etree.Element
            The newly added person.
        """
        logging.info(
            "Adding person with id {} to the person list.".format(person_id))
        if self._contains_invalid_characters(person_id):
            self._add_id_to_post_processing(person_id)
        person = etree.SubElement(person_list, XmlElements.person)
        person.set(XmlAttributes.xml_id, person_id)
        person_name = etree.SubElement(person, XmlElements.persName)
        for part in first_name:
            forename = etree.SubElement(person_name, XmlElements.forename)
            forename.text = part.capitalize()
        for part in last_name:
            surname = etree.SubElement(person_name, XmlElements.surname)
            surname.text = part.capitalize()
        sex = etree.SubElement(person, XmlElements.sex)
        sex.set(XmlAttributes.value, gender[0])
        sex.text = gender
        if (image_url is not None) and (len(image_url) > 0):
            logging.info("Person with id {} has image URL {}.".format(
                person_id, image_url))
            figure = etree.SubElement(person, XmlElements.figure)
            graphic = etree.SubElement(figure, XmlElements.graphic)
            graphic.set(XmlAttributes.url, image_url)
        self.existing_persons[person_id] = person
        return person

    def _add_id_to_post_processing(self, id_string):
        """Adds the specified id_string to the list of ids to be replaced.

        Parameters
        ----------
        id_string: str, required
            The id containing invalid characters.
        """
        logging.info(
            "Person id {} contains invalid characters.".format(id_string))
        if id_string in self.ids_to_replace:
            logging.info(
                "Id {} is already in the post-processing list.".format(
                    id_string))
            return
        canonical_id = self._build_canonical_id(id_string)
        logging.info("Scheduling id {} to be replaced with {}.".format(
            id_string, canonical_id))
        self.ids_to_replace[id_string] = canonical_id

    def _build_canonical_id(self, id_string):
        """Builds a canonical form of the `id_string` by replacing invalid characters.

        Parameters
        ----------
        id_string: str, required
            The id to make canonical.

        Returns
        -------
        canonical_id: str
            The id where all the invalid characters were replaced.
        """
        invalid_characters = [
            letter for letter in id_string
            if letter in self.id_char_replacements
        ]

        canonical_id = id_string
        for c in invalid_characters:
            replacement = self.id_char_replacements[c]
            canonical_id = canonical_id.replace(c, replacement)

        return canonical_id

    def _contains_invalid_characters(self, id_string):
        """Checks if the provided id contains invalid characters.

        Parameters
        ----------
        id_string: str, required
            The id to check.

        Returns
        -------
        contains_invalid_chars: bool
            True if id contains invalid characters; False otherwise.
        """
        for letter in id_string:
            if letter in self.id_char_replacements:
                return True
        return False

    def _add_unknown_speaker(self, person_list, speaker_id):
        """Adds an unknown speaker to the list of persons by trying to guess its name and gender.

        Parameters
        ----------
        person_list: etree.Element, required
            The element to which to add new speaker if it does not exist.
        speaker_id: str, required
            The id of the unknown speaker without the leading # symbol.
        """
        logging.info(
            "Id {} not found in name map. Inferring deputy info.".format(
                speaker_id))
        name_parts = speaker_id.split('-')
        first_name = name_parts[:-1]
        last_name = name_parts[-1:]
        self._add_person(person_list, speaker_id, first_name, last_name,
                         self._guess_gender(first_name))

    def _guess_gender(self, first_names):
        """Tries to guess the gender of a person by looking at its first names.

        Parameters
        ----------
        first_names: iterable of str, required
            The first names of the person.

        Returns
        -------
        gender: str
            The values can be 'Male' or 'Female'.
        """
        for part in first_names:
            if part in self.male_names:
                return Gender.Male
            if part in self.female_names:
                return Gender.Female
        # None of the first names are known
        # Try to infer the gender
        for part in first_names:
            if part[-1] == 'a':
                return Gender.Female
        return Gender.Male

    def _split_names_by_gender(self):
        """Iterates over the names map and splits the first names into male and female specific.
        """
        for dep_info in self.name_map.values():
            first_names = dep_info.first_name.replace('-', ' ').split()
            for first_name in first_names:
                if dep_info.gender == 'M':
                    self.male_names.add(first_name)
                else:
                    self.female_names.add(first_name)

    def _update_tag_usage(self, corpus_component):
        """Updates the `tagUsage` element with the values from `corpus_component.

        Parameters
        ----------
        corpus_component: etree.ElementTree, required
            The contents of the component file as an XML tree.
        """
        logging.info("Updating tagUsage.")
        tag_usage_component = {
            tu.get(XmlAttributes.gi): int(tu.get(XmlAttributes.occurs))
            for tu in corpus_component.iterdescendants(
                tag=XmlElements.tagUsage)
        }

        tag_usage_root = {
            tu.get(XmlAttributes.gi): tu
            for tu in self.corpus_root.iterdescendants(
                tag=XmlElements.tagUsage)
        }

        for tag_type, num_occurences in tag_usage_component.items():
            elem = tag_usage_root[tag_type]
            num_occurences = num_occurences + int(
                elem.get(XmlAttributes.occurs))
            logging.info("Setting {} tag usage to {} occurences.".format(
                tag_type, num_occurences))
            elem.set(XmlAttributes.occurs, str(num_occurences))

    def _iter_files(self, corpus_dir, root_file):
        """Iterates over the files in the `corpus_dir` and skips `root_file`.

        Parameters
        ----------
        corpus_dir: pathlib.Path, required
            The path of the corpus directory.
        root_file: str, required
            The name of the corpus root file to be skipped.

        Returns
        -------
        file_path: generator of pathlib.Path
            The generator that returns path of each component file.
        """
        for file_path in corpus_dir.glob('*.xml'):
            if not root_file in str(file_path):
                yield file_path

    def _parse_terms_list(self, parliament_id):
        """Builds a list of parliament terms with their dates and event ids.

        Returns
        -------
        terms: list of (start_date, end_date, id) tuples
            The terms of the parliament. The parts `start_date` and `end_date` are dates and `id` is str.
        """
        parliament = None
        for org in self.corpus_root.iterdescendants(XmlElements.org):
            if org.get(XmlAttributes.xml_id) == parliament_id:
                parliament = org
                break
        if parliament is None:
            logging.error(
                "Could not find organization with role='parliament'.")
            return []

        terms = []
        for event in parliament.iterdescendants(XmlElements.event):
            id = event.get(XmlAttributes.xml_id)
            start_date = parser.parse(event.get(XmlAttributes.event_start))
            end_date_str = event.get(XmlAttributes.event_end)
            end_date = parser.parse(event.get(
                XmlAttributes.event_end)) if end_date_str is not None else None
            terms.append((start_date, end_date, id))
        return terms

    def _build_name_map(self, deputy_info):
        """Builds a map of speaker ids and their names from the affiliations.

        Parameters
        ----------
        deputy_info: pandas.DataFrame, required
            The DataFrame containing depity info records.

        Returns
        -------
        name_map: dict of (str, str)
            A dict containing speaker ids as keys and speaker names as values.
        """

        name_map = {}
        for row in deputy_info.itertuples():
            name_parts = [row.first_name, row.last_name]
            value = DeputyInfo(first_name=row.first_name,
                               last_name=row.last_name,
                               gender=row.gender,
                               image_url=row.image_url)
            self._add_to_name_map(name_map, name_parts, value)
            # Reverse the name parts to make sure we don't loose any data
            name_parts.reverse()
            self._add_to_name_map(name_map, name_parts, value)
        return name_map

    def _add_to_name_map(self, name_map, name_parts, value):
        """Adds the specified value to the name_map under different key variations.

        Parameters
        ----------
        name_map: dict of (str, str), required
            The name map to add to.
        name_parts: iterable of str, required
            First and last name.
        value: DeputyInfo, required
            The value to add to the name map;
        """
        id = build_speaker_id(' '.join(name_parts))
        id = self._build_name_map_key(id)
        if id not in name_map:
            name_map[id] = value

    def _build_name_map_key(self, id):
        """Converts the given id into a canonical representation for the name map.

        Parameters
        ----------
        id: str, required
            The id to normalize.

        Returns
        -------
        canonical_id: str
            The normalized id.
        """
        if id[0] != '#':
            id = '#{}'.format(id)
        canonical_id = id.lower()
        return canonical_id

    def _normalize_last_name(self, last_name):
        """Capitalizes each part of the last name.

        Parameters
        ----------
        last_name: str, required
            The name to normalize.

        Returns
        -------
        normalized: str
            The normalized name.
        """
        name = last_name.replace('-', ' ').split()
        normalized = '  '.join([p.capitalize() for p in name])
        return normalized

    def _write_file(self, file_name):
        """Saves the corpus root XML to specified file.

        Parameters
        ----------
        file_name: str, required
            The name of the output file.
        """
        file_name = Path(self.corpus_dir, file_name)
        file_name = str(file_name)
        save_xml(self.xml_root, file_name)

    def _build_organizations_list(self):
        """Builds the list of organizations from affiliation records.
        """
        orgList = None
        for elem in self.corpus_root.iterdescendants(tag=XmlElements.listOrg):
            orgList = elem
            break
        if orgList is None:
            logging.error("Could not find element listOrg in template file.")
            return
        for org in self.organizations:
            name, acronym = parse_organization_name(org)
            role = self._get_organization_role(name)
            self._build_organization_element(orgList, name, acronym, role)

    def _build_organization_element(self, parent, name, acronym, role):
        """Builds an `org` element and adds it to the parent element.

        Parameters
        ----------
        parent: etree.Element, required
            The parent element to which to append the newly created `org` element.
            Usually it's the `listOrg` element.
        name: str, required
            Full name of the organization.
        acronym: str, required
            The acronym of the organization. Can be None.
        role: str, required
            The role of the organization.
        """
        org_element = etree.SubElement(parent, XmlElements.org)
        org_element.set(XmlAttributes.xml_id,
                        self._build_organization_id(name, acronym))
        org_element.set(XmlAttributes.role, role)
        name_element = etree.SubElement(org_element, XmlElements.orgName)
        name_element.set(XmlAttributes.full, "yes")
        name_element.set(XmlAttributes.lang, "ro")
        name_element.text = name

        if (acronym is not None) and (len(acronym) > 0):
            acronym_element = etree.SubElement(org_element,
                                               XmlElements.orgName)
            acronym_element.set(XmlAttributes.full, "init")
            acronym_element.text = acronym

    def _get_organization_role(self, organization_name):
        """Returns the organization role based on its name.

        Parameters
        ----------
        organization_name: str, required
            The name of the organization.

        Returns
        -------
        role: str
            The role of the organization.
        """
        if Resources.PoliticalGroupOfEthnicMinorities in organization_name:
            return OrganizationType.EthnicCommunity
        if Resources.PoliticalGroup in organization_name:
            return OrganizationType.PoliticalGroup
        if OrganizationType.Independent.lower() in organization_name.lower():
            return OrganizationType.Independent
        if Resources.Unaffiliated.lower() == organization_name.lower():
            return OrganizationType.Independent
        if Resources.NoAdherence.lower() == organization_name.lower():
            return OrganizationType.Independent
        return OrganizationType.PoliticalParty

    def _build_organization_id(self, name, acronym):
        """Builds the id of an organization based on its properties.

        Parameters
        ----------
        name: str, required
            The full name of the organization.
        acronym: str, required
            The acronym of the organization.

        Returns
        -------
        id: str
            The id of the organization.
        """
        pattern = "RoParl.Org.{}"
        if (acronym is not None) and (len(acronym) > 0):
            org_id = pattern.format(acronym)
            return self._build_canonical_id(org_id)

        replacements = {'(': '', ')': '', '-': ' '}
        for char, replacement in replacements.items():
            name = name.replace(char, replacement)
        parts = name.split()
        if len(parts) > 1:
            acronym = [
                part[0].upper() if not part.isupper() else part
                for part in parts
            ]
            return self._build_canonical_id(pattern.format(''.join(acronym)))

        return self._build_canonical_id(pattern.format(name.capitalize()))


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
        self.segment_index = 0

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
        return build_speaker_id(speaker)

    def build_utterance_id(self):
        """Builds the id of the current utterance.

        Returns
        -------
        utterance_id: str
            The id of the current utterance.
        """
        self.utterance_index = self.utterance_index + 1
        return "{}.u{}".format(self.session_id, self.utterance_index)

    def build_segment_id(self):
        """Builds the id of the current segment.

        Returns
        -------
        segment_id: str
            The id of the current segment.
        """
        self.segment_index = self.segment_index + 1
        return "{}.seg{}".format(self.session_id, self.segment_index)

    def _build_session_id(self):
        """Builds the session id from the date and file prefix.

        Returns
        -------
        session_id: str
            The id of the session.
        """
        session_id = "{}_{}-CD".format(
            self.prefix, format_date(self.session_date, "yyyy-MM-dd"))
        return session_id
