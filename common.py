import re


def build_speaker_id(speaker_name):
    """Builds the id of the speaker from its name.

    Parameters
    ----------
    speaker_name: str
        The name of the speaker.

    Returns
    -------
    speaker_id: str
        The id of the speaker.
    """
    canonical_name = re.sub(r'\s+', '-', speaker_name, 0, re.MULTILINE)
    speaker_id = "#{}".format(canonical_name)
    return speaker_id


def get_element_text(element):
    """Builds the element text by iterating through child elements.

    Parameters
    ----------
    element: lxml.Element
        The element for which to build text.

    Returns
    -------
    text: str
        The inner text of the element.
    """
    text = ''.join(element.itertext())
    return text


class OrganizationType:
    """Represents types of organizations to which deputies are affiliated.
    """
    PoliticalParty = "politicalParty"
    EthnicCommunity = "ethnicCommunity"
    Independent = "independent"


class SessionType:
    """Encodes the values for session types.
    """
    Ordinary = 's'
    Extraordinary = 'se'
    Joint = 'sc'
    JointSolemn = 'scs'
    JointVisit = 'scv'


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
    SessionStartMark = "ședința a început la ora"
    SessionEndMark = "încheiat la ora"
    AffiliationStartDateMark = "din"
    PoliticalParty = "Formațiunea politică"
    PoliticalGroup = "Grupul parlamentar"
    PresentTime = "prezent"
    Transcript = "Stenograma"
    TranscriptSpaced = "S T E N O G R A M A"


class StringFormatter:
    """Formats the strings parsed from the session transcription.
    """
    def __init__(self):
        """Creates a new instance of StringFormatter.
        """
        self.translations = str.maketrans({
            'þ': 'ț',
            'º': 'ș',
            'Þ': 'Ț',
            'ã': 'ă',
            'ª': 'Ș',
            '\226': '\u2013'
        })

    def to_single_line(self, value):
        """Removes line feed/carriage returns from given string.

        Parameters
        ----------
        value: str, required
            The string to convert to single line.
        """
        line = " ".join([l.strip() for l in value.splitlines()])
        return self.normalize(line)

    def normalize(self, value):
        """Normalizes the string by stripping whitespace and translating diacritics.

        Parameters
        ----------
        value: str, required
            The string to normalize.
        """
        return value.strip().translate(self.translations)
