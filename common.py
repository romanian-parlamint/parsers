import re


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
