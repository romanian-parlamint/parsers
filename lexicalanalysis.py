from conllu import parse as parse_conllu
import spacy_udpipe as sup
import requests


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
