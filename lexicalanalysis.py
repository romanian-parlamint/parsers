from conllu import parse as parse_conllu
import requests
from pathlib import Path
from xmlbuilder import parse_xml_file, save_xml, XmlAttributes, XmlElements, add_component_file_to_corpus_root
import logging
from lxml import etree


class CorpusIterator:
    def __init__(self, corpus_dir, root_file):
        """Creates a new instance of CorpusIterator.

        Parameters
        ----------
        corpus_dir : str, required
            The path to the corpus directory.
        root_file : str, required
            The name of the root file in corpus.
        """
        self.corpus_dir = Path(corpus_dir)
        self.corpus_root_file = Path(self.corpus_dir, root_file)
        self.annotated_corpus_root_file = Path(
            self.corpus_dir, "{}.ana.xml".format(self.corpus_root_file.stem))

    @property
    def root_file(self):
        """Gets the root file of the corpus.

        Returns
        -------
        root_file: pathlib.Path
            The path of the root file.
        """
        return self.corpus_root_file

    @property
    def annotated_root_file(self):
        """Gets the annotated root file of the corpus.

        Returns
        -------
        annotated_root_file: pathlib.Path
            The path of the annotated root file.
        """
        return self.annotated_corpus_root_file

    def iter_corpus_files(self, skip_annotated=False):
        """Iterates over corpus files.

        Parameters
        ----------
        skip_annotated: bool, optional
            Specifies whether to iterate over all corpus files or just the ones that are not annotated.
            Default is False which means iterate over all corpus files.

        Returns
        -------
        file_generator: generator of pathlib.Path
            The generator that iterates corpus files one by one.
        """
        annotated_files = set()
        if skip_annotated:
            annotated_files = set([
                self._get_file_name_without_extensions(f)
                for f in self.iter_annotated_files()
            ])

        for file_path in self.corpus_dir.glob("*.xml"):
            if file_path == self.root_file:
                continue
            if ('.ana' not in file_path.suffixes) and (file_path.stem
                                                       not in annotated_files):
                yield file_path

    def iter_annotated_files(self):
        """Iterates over annotated corpus files.

        Returns
        -------
        file_generator: generator of pathlib.Path
            The generator that iterates annotated corpus files one by one.
        """
        for file_path in self.corpus_dir.glob("*.ana.xml"):
            if file_path == self.annotated_root_file:
                continue
            yield file_path

    def get_component_file_name(self, file_path):
        """Gets the name of the component file associated with the provided file.

        Parameters
        ----------
        file_path: pathlib.Path, required
            The path of the file for which to get the component file.

        Returns
        -------
        component_file: pathlib.Path
            The component file path.
        """
        stem = self._get_file_name_without_extensions(file_path)
        component_file = Path(file_path).with_stem(stem)
        component_file = component_file.with_suffix(".xml")
        return component_file

    def _get_file_name_without_extensions(self, file_path):
        """Gets the file name by replacing all extensions with empty strings.

        Parameters
        ----------
        file_path: pathlib.Path, required
            The path of the file.

        Returns
        -------
        stem: str
            File name without extensions.
        """
        stem = file_path.stem
        for ext in file_path.suffixes:
            stem = stem.replace(ext, '')
        return stem


class UDPipe:
    """Wrapper class for making requests to UDPipe API.
    """
    def __init__(self,
                 url='http://lindat.mff.cuni.cz/services/udpipe/api/process',
                 model_name='romanian-rrt-ud-2.6-200830',
                 use_tokenizer=True,
                 use_parser=True,
                 use_tagger=True):
        """Creates a new instance of UDPipe class.

        Parameters
        ----------
        url: str, optional
            The URL of the process endpoint.
            Default value is `http://lindat.mff.cuni.cz/services/udpipe/api/process`.
        model_name: str, optional
            The name of the model to use when processing text.
            Default value is `romanian-rrt-ud-2.6-200830`.
        use_tokenizer: bool, optional
            Specifies whether to use tokenizer module or not from the model.
            Default is `True`.
        use_parser: bool, optional
            Specifies whether to use parser module or not from the model.
            Default is `True`.
        use_tagger: bool, optional
            Specifies whether to use tagger module or not from the model.
            Default is `True`.
        """
        self.url = url
        self.parameters = {
            'tokenizer': 'true' if use_tokenizer else 'false',
            'parser': 'true' if use_parser else 'false',
            'tagger': 'true' if use_tagger else 'false',
            'model': model_name
        }

    def process(self, text):
        """Processes the given text using UDPipe.

        Parameters
        ----------
        text: str, required
            The text to process using UDPipe.

        Returns
        -------
        document: list of conllu.models.TokenList
            The processed text in CoNLL-U format.
        """
        payload = dict(self.parameters)
        payload['data'] = text
        response = requests.post(self.url, data=payload)
        document = response.json()
        document = parse_conllu(document['result'])
        return document


class TagUsageCounter:
    """Class responsible for updating tagUsage elements within a XML document.
    """
    def __init__(self):
        """Initializes a new instance of TagUsageCounter.
        """
        self.name_map = {
            's': XmlElements.s,
            'w': XmlElements.w,
            'pc': XmlElements.pc,
            'linkGrp': XmlElements.linkGrp,
            'link': XmlElements.link
        }

    def update_tag_usage(self, tag_usage_root, countable_elements_root):
        """Updates the tag usage declaration with statistics for lexical annotation tags.

        Parameters
        ----------
        tag_usage_root: etree.Element, required
            The element that has tagUsage elements to be updated as its descendants.
        countable_elements_root: etree.Element, required
            The element that has nodes to be counted.
        """
        for key, tag in self.name_map.items():
            element = self._get_or_add_tag_usage(tag_usage_root, key)
            value = element.get(XmlAttributes.occurs)
            if (value is not None) and (len(value) > 0):
                value = int(value)
            tags = [
                t for t in countable_elements_root.iterdescendants(tag=tag)
            ]
            value = value + len(tags)
            element.set(XmlAttributes.occurs, str(value))

    def _get_or_add_tag_usage(self, tag_usage_root, gi_value):
        """Searches for a `tagUsage` element with the provided gi attribute. If not found, creates it.

        Parameters
        ----------
        tag_usage_root: etree.Element, required
            The element that has tagUsage elements as its descendants.
        gi_value: str, required
            The value of `gi` attribute.

        Returns
        -------
        tag_usage: etree.Element
            The tagUsage element.
        """
        for tag_usage in tag_usage_root.iterdescendants(
                tag=XmlElements.tagUsage):
            if tag_usage.get(XmlAttributes.gi) == gi_value:
                return tag_usage
        parent = tag_usage.getparent()
        tag_usage = etree.SubElement(parent, XmlElements.tagUsage)
        tag_usage.set(XmlAttributes.gi, gi_value)
        tag_usage.set(XmlAttributes.occurs, '0')
        return tag_usage


class LinkGroupBuilder:
    """Builds the `linkGrp` element of a sentence.
    """
    def __init__(self, sentence):
        """Creates a new instance of LinkGroupBuilder for the specified sentence.
        """
        self.conllu_sentence = sentence

    def build_from(self, conllu_sentence):
        """Builds the `linkGrp` element from the provided sentence in CoNLL-U format.

        Parameters
        ----------
        conllu_sentence: conllu.models.TokenList, required
            The sentence in CoNLL-U format.
        """
        linkGrp = self._build_link_group_element(self.sentence)
        for token in conllu_sentence:
            _ = self._add_link_to_group(token, conllu_sentence, linkGrp)

    def _add_link_to_group(self, token, sentence, link_group):
        """Adds a `link` element to the specified `linkGrp` element.

        Parameters
        ----------
        token: conllu.models.Token, required
            The token that is the origin of the link.
        sentence: conllu.models.TokenList, required
            The list of tokens containing the head element.
        link_group: etree.Element, required
            The parent `linkGrp` element.

        Returns
        -------
        link: etree.Element
            The newly created `link` element or None if token is the root element.
        """
        head = None
        for tok in sentence:
            if tok['id'] == token['head']:
                head = tok
                break
        link = etree.Element(XmlElements.link)
        rel = "ud-syn:{}".format(token['deprel']).replace(':', '_')
        link.set(XmlAttributes.ana, rel)
        if (head is None) and (len(sentence) > 1):
            # token is the root element
            tail_node_id = head['misc'][XmlAttributes.xml_id]
            head_node_id = link_group.getparent().get(XmlAttributes.xml_id)
            link.set(
                XmlAttributes.target,
                "#{head} #{tail}".format(tail=tail_node_id, head=head_node_id))
            return None
        tail_node_id = token['misc'][XmlAttributes.xml_id]
        if head is not None:
            head_node_id = head['misc'][XmlAttributes.xml_id]
            link.set(
                XmlAttributes.target,
                "#{head} #{tail}".format(tail=tail_node_id, head=head_node_id))
        else:
            link.set(XmlAttributes.target, '#{}'.format(tail_node_id))
        link_group.append(link)

    def _build_link_group_element(self, sentence_elem):
        """Adds the `linkGrp` element to the `s` element.

        Returns
        -------
        link_group: etree.Element
            The newly created `linkGrp` element.
        """
        link_group = etree.SubElement(self.sentence, XmlElements.linkGrp)
        link_group.set(XmlAttributes.targFunc, "head argument")
        link_group.set(XmlAttributes.type_, "UD-SYN")
        return link_group


class CorpusComponentAnnotator:
    """Applies linguistic annotation to a corpus component file.
    """
    def __init__(self, component_file, udpipe):
        """Creates a new instance of CorpusComponentAnnotator for the specified file.

        Parameters
        ----------
        component_file : pathlib.Path
            The path of the component file.
        udpipe: UDPipe, required
            The wrapper instance of UDPipe to process files.
        """
        self.file_name = str(component_file)
        self.component_file = component_file
        self.udpipe = udpipe
        annotated_file, conllu_file = self._build_output_file_names(
            self.component_file)
        self.annotated_file = annotated_file
        self.conllu_file = conllu_file
        self.xml = parse_xml_file(self.file_name)
        self.corpus_component = self.xml.getroot()
        self.last_document_id = None
        self.last_paragraph_id = None
        self.conllu_doc = []

    def apply_annotation(self):
        """Applies linguistic annotations to the file.
        """
        logging.info("Annotating file {}.".format(self.file_name))
        for seg in self.corpus_component.iterdescendants(tag=XmlElements.seg):
            document_id = self._get_document_id(seg)
            paragraph_id = seg.get(XmlAttributes.xml_id)
            logging.info("Processing segment {} of utterance {}".format(
                paragraph_id, document_id))
            if (seg.text is not None) and (len(seg.text) > 0):
                sentences = self.udpipe.process(seg.text)
                self._replace_segment_text(seg, sentences)
                self._append_sentences_to_output(sentences, document_id,
                                                 paragraph_id)
        self._update_tag_usage()
        save_xml(self.xml, str(self.annotated_file))
        self._write_conllu()

    def _update_tag_usage(self):
        """Updates the tag usage declaration with statistics for lexical annotation tags.
        """
        counter = TagUsageCounter()
        counter.update_tag_usage(self.corpus_component, self.corpus_component)

    def _replace_segment_text(self, segment, sentences):
        """Replaces the text of the specified segment with the provided sentences.

        Parameters
        ----------
        segment : etree.Element, required
            The segment whose text is to be replaced.
        sentences :
            The sentences that will replace the segment text.
        """
        segment.text = None
        for sentence in sentences:
            s = self._add_sentence_to_segment(sentence, segment)
            for token in sentence:
                elem = self._add_token_to_sentence(token, s)
                self._add_xml_id_to_token(elem.get(XmlAttributes.xml_id),
                                          token)
            builder = LinkGroupBuilder(s)
            builder.build_from(sentence)

    def _add_xml_id_to_token(self, xml_id, token):
        """Adds the provided xml_id to the `misc` category of the token.

        Parameters
        ----------
        xml_id: str, required
            The id to add to the token.
        token: conllu.models.Token, required
            The token to which to add the XML id.
        """
        if ('misc' not in token) or (token['misc'] is None):
            token['misc'] = {}
        token['misc'][XmlAttributes.xml_id] = xml_id

    def _add_sentence_to_segment(self, sentence, segment):
        """Adds the `s` element to the provided segment.

        Parameters
        ----------
        sentence: conllu.models.TokenList, required
            The sentence to add.
        segment: etree.Element, required
            The segment to which to add the sentence.

        Returns
        -------
        s: etree.Element
            The newly created `s` element.
        """
        sentence_id = sentence.metadata['sent_id']
        segment_id = segment.get(XmlAttributes.xml_id)
        sentence_id = '{}.{}'.format(segment_id, sentence_id)
        s = etree.SubElement(segment, XmlElements.s)
        s.set(XmlAttributes.xml_id, sentence_id)
        return s

    def _add_token_to_sentence(self, token, sentence_elem):
        """Adds the token to the specified s(entence) element in XML file.

        Parameters
        ----------
        token: conllu.models.Token, required
            The CoNLL-U token.
        sentence_elem: etree.Element, required
            The `<s>` element to which to append current token.

        Returns
        -------
        token_elem: etree.Element
            The newly created token element.
        """
        elem_name = XmlElements.w
        if token['upos'] == "PUNCT":
            elem_name = XmlElements.pc
        token_elem = etree.SubElement(sentence_elem, elem_name)
        token_id = '{}.{}'.format(sentence_elem.get(XmlAttributes.xml_id),
                                  token['id'])
        token_elem.set(XmlAttributes.xml_id, token_id)
        token_elem.text = token['form']
        if elem_name == XmlElements.w:
            token_elem.set(XmlAttributes.lemma, token['lemma'])
        token_elem.set(XmlAttributes.pos, token['xpos'])
        msd = ["UPosTag={}".format(token['upos'])]
        if ('feats' in token) and (token['feats'] is not None):
            msd = msd + [
                '{}={}'.format(k, v) for k, v in token['feats'].items()
            ]
        token_elem.set(XmlAttributes.msd, '|'.join(msd))
        return token_elem

    def _append_sentences_to_output(self, sentences, document_id,
                                    paragraph_id):
        """Appends the provided sentences to the list of CoNLL-U annotations.

        Parameters
        ----------
        sentences : list of TokenList
            The processed sentences.
        document_id : str, required
            The document id of the sentences.
        paragraph_id : str, required
            The paragraph id of the sentences.
        """
        head_sentence = sentences[0]
        if len(self.conllu_doc) > 0:
            head_sentence.metadata.pop('generator')
            head_sentence.metadata.pop('udpipe_model')
            head_sentence.metadata.pop('udpipe_model_licence')
        if self.last_document_id != document_id:
            head_sentence.metadata['newdoc'] = 'id = {}'.format(document_id)
            self.last_document_id = document_id
        else:
            head_sentence.metadata.pop('newdoc')

        if self.last_paragraph_id != paragraph_id:
            head_sentence.metadata['newpar'] = 'id = {}'.format(paragraph_id)
            self.last_paragraph_id = paragraph_id
        else:
            head_sentence.metadata.pop('newpar')

        for s in sentences:
            self.conllu_doc.append(s.serialize())

    def _get_document_id(self, segment):
        """Gets the document id for the specified segment. The document id is the id of the parent u element.

        Parameters
        ----------
        segment : etree.Element, required
            The segment for which to extract document id.

        Returns
        -------
        document_id : str
            The document id for the specified segment.
        """
        u = segment.getparent()
        document_id = u.get(XmlAttributes.xml_id)
        return document_id

    def _write_conllu(self):
        """Writes the CoNLL-U annotated sentences to a file.
        """
        file_name = str(self.conllu_file)
        logging.info("Saving CoNLL-U document to {}.".format(file_name))
        with open(file_name, 'wt', encoding='utf-8') as f:
            for s in self.conllu_doc:
                f.write(s)

    def _build_output_file_names(self, file_path):
        """Builds the file names for the annotated component file and CoNLL-U file.

        Parameters
        ----------
        file_path : pathlib.Path, required
            The path of the component file from which to infer output file names.

        Returns
        -------
        (annotated_file, conllu_file) : tuple of (pathlib.Path, pathlib.Path)
            The names of output files.
        """
        parent = file_path.parent
        stem = file_path.stem
        annotated_file = Path(parent, '{}.ana.xml'.format(stem))
        conllu_file = Path(parent, '{}.conllu'.format(stem))
        return annotated_file, conllu_file


class AnnotatedFilesAggregator:
    """Aggregates the info from annotated files and saves it into the root file.
    """
    def __init__(self, corpus_iterator):
        """Creates a new instance of AnnotatedFilesAggregator.

        Parameters
        ----------
        corpus_iterator : CorpusIterator, required
            The iterator instance that provides access to annotated files and root file.
        """
        self.corpus_iterator = corpus_iterator
        self.root_file = str(corpus_iterator.annotated_root_file)
        self.xml = parse_xml_file(self.root_file)
        self.corpus_root = self.xml.getroot()

    def aggregate_corpus_info(self):
        """Iterates over annotated corpus files and aggregates their info into the root file.
        """
        counter = TagUsageCounter()
        for component_file in self.corpus_iterator.iter_annotated_files():
            component = parse_xml_file(str(component_file)).getroot()
            counter.update_tag_usage(self.corpus_root, component)
            add_component_file_to_corpus_root(component_file, self.corpus_root)
        save_xml(self.xml, self.root_file)
