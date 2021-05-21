from argparse import ArgumentParser
import requests
import logging
import re
from lxml import etree, html
import pandas as pd
from common import get_element_text
from common import OrganizationType
from urllib.parse import urlparse, parse_qs
from collections import namedtuple
from datetime import date
from common import Resources


class XPathStrings:
    DeputiesTableBody = "//div[@class='grup-parlamentar-list grupuri-parlamentare-list']/table/tbody"
    DeputyInfoDiv = "//div[@id='oldDiv']"
    ProfilePic = "//a[@class='highslide ']/img"  # The space at te end of class name is also present in the page!
    InfoSections = "//div[@class='boxDep clearfix']"


class MandateType:
    Deputy = 'deputat'
    Senator = 'senator'


Affiliation = namedtuple('Affiliation',
                         ['organization', 'start_date', 'end_date'])


class MandateInfoParser:
    """Parses the information from a page describing a deputy mandate.
    """
    def __init__(self, url, name, start_year, end_year=None):
        """Creates a new instance of MandateInfoParser.

        Parameters
        ----------
        url : str, required
            The url of the term/mandate page.
        name : str, required
            The name of the deputy.
        start_year: int, required
            The start year of the term/mandate.
        end_year: int, optional
            The end year of the term/mandate. Default is None which means that the term is ongoing.
        """
        self.url = url
        self.name = name
        self.start_year = start_year
        self.end_year = end_year
        self.date_regex = re.compile(r'([a-z]{3})\.\s+([0-9]{4})',
                                     re.IGNORECASE)
        self.month_map = {
            'ian': 1,
            'feb': 2,
            'mar': 3,
            'apr': 4,
            'mai': 5,
            'iun': 6,
            'iul': 7,
            'aug': 8,
            'sep': 9,
            'oct': 10,
            'noi': 11,
            'dec': 12
        }
        self.html_root = self._load_page(self.url)

    def parse_deputy_id(self):
        """Parses the id of the deputy in the underlying database.

        Returns
        -------
        deputy_id: int
            The id of the deputy.
        """
        if self.url is None:
            logging.error("Url not set.")
        url_parts = urlparse(self.url)
        query_string = parse_qs(url_parts.query)
        return int(query_string['idm'][0])

    def parse_affiliations(self):
        """Parses the affiliation for the current term.

        Returns
        -------
        affiliations: iterable of Affiliation
            The collection of affiliations for the current term.
        """
        logging.info("Parsing affiliations for page '{}'.".format(self.url))
        affiliation_section = self.html_root.xpath(XPathStrings.InfoSections)
        if (affiliation_section is None) or (len(affiliation_section) < 2):
            logging.error(
                "Could not find affiliations section for page '{}'.".format(
                    self.url))
            return []
        affiliation_section = affiliation_section[1]
        title = self._get_affiliation_title(affiliation_section)
        logging.info(
            "Title of the affiliations section for page '{}' is: '{}'.".format(
                self.url, title))
        info_table = next(affiliation_section.iterdescendants(tag='table'))
        affiliations = []
        for row in info_table:
            text = get_element_text(row)
            affiliations.append(self._parse_affiliation(text))

        return affiliations

    def _parse_affiliation(self, text):
        """Parses the organization name and dates for an affiliation period.

        Parameters
        ----------
        text : str, required
            The text from which to parse the affiliation info.

        Returns
        -------
        affiliation : Affiliation
            The named tuple containing affiliation info.
        """
        organization, dates = [], []
        for p in text.split('-'):
            p = p.strip()
            # Search for a string in the format `mmm. yyyy'
            # If found then the current segment is a date
            # Otherwise it is part of the organization name
            if self.date_regex.search(p):
                dates.append(p)
            else:
                organization.append(p)

        organization_name = '-'.join(organization)
        start_date, end_date = self._parse_affiliation_dates(dates)
        affiliation = Affiliation(organization=organization_name,
                                  start_date=start_date,
                                  end_date=end_date)
        return affiliation

    def _parse_affiliation_dates(self, date_strings):
        """Returns the start and end date from the provided parameters.

        Parameters
        ----------
        date_strings: iterable of str

        Returns
        -------
        (start_date, end_date): tuple of datetime.date
            The start and end dates of the affiliation. End date may be None.
        """
        start_date = date(self.start_year, 1, 1)
        end_date = None
        if self.end_year is not None:
            end_date = date(self.end_year, 1, 1)
        for date_str in date_strings:
            if Resources.AffiliationStartDateMark in date_str:
                start_date = self._parse_date(date_str)
            else:
                end_date = self._parse_date(date_str)

        return start_date, end_date

    def _parse_date(self, date_str):
        """Parses the date from the provided string.

        Parameters
        ----------
        date_str: str
            The string containing a start/end date of the affiliation.

        Returns
        -------
        dt: datetime.date
            The date parsed from the provided string or None.
        """
        logging.info(
            "Parsing affiliation date from string '{}'.".format(date_str))
        match = self.date_regex.search(date_str)
        if match is None:
            logging.info("Date regex did not match the provided string.")
            print("no match")
            return None

        month = match.group(1).lower().strip('.')
        year = int(match.group(2))
        logging.info(
            "The following date parts were found: month={}, year={}.".format(
                month, year))
        return date(year, self.month_map[month], 1)

    def _get_affiliation_title(self, affiliation):
        """Returns the title of affiliation section.

        Parameters
        ----------
        affiliation :  etree.ElementTreee
            The HTML element containing the affiliation info.

        Returns
        -------
        title : str
            The title of the affiliation section or None.
        """
        h3 = next(affiliation.iterdescendants(tag='h3'))
        if h3 is None:
            logging.error(
                "Could not parse the title of the affiliations section for page '{}'."
                .format(self.url))
            return None
        title = get_element_text(h3)
        return title.replace(':', '').strip()

    def _load_page(self, url):
        """Retrieves and parses the html of the page into a html element.

        Parameters
        ----------
        url : str, required
            The URL of the page to load.

        Returns
        -------
        html_root : etree.Element
            The root element of the page.
        """
        response = requests.get(url)
        html_root = html.fromstring(response.content)
        return html_root


def parse_deputies_table(tbody):
    """Parses the body of table containing deputy records into a dict.

    Parameters
    ----------
    tbody: etree.Element
        The table body (without header) element.

    Returns
    -------
    records: pandas.DataFrame
    """
    def is_complete_row(tr):
        return len(tr) == 4

    idx, name, period, mandate = None, None, None, None
    data = {
        'order_num': [],
        'name': [],
        'period': [],
        'mandate': [],
        'period_link': []
    }
    logging.info("Parsing deputies table.")
    for row_num, row in enumerate(tbody):
        logging.info("Parsing row number {}.".format(row_num))
        if is_complete_row(row):
            logging.debug("Row {} is complete.".format(row_num))
            idx, name, period, mandate = row
        else:
            logging.debug("Row {} is incomplete.".format(row_num))
            period, mandate = row

        deputy_num = int(float(idx.text))
        deputy_name = get_element_text(name)
        period_text = get_element_text(period)
        mandate_text = get_element_text(mandate)
        href = period[0].get('href')
        logging.info("Values: [{}, {}, {}, {}]".format(deputy_num, deputy_name,
                                                       period_text,
                                                       mandate_text))
        data['order_num'].append(deputy_num)
        data['name'].append(deputy_name)
        data['period'].append(period_text)
        data['mandate'].append(mandate_text)
        data['period_link'].append(href)
    logging.info("Finished parsing deputies table.")
    records = pd.DataFrame.from_dict(data)
    return records


def parse_deputy_mandate_info(html, url):
    container = html.xpath(XPathStrings.DeputyInfoDiv)
    if container is None:
        logging.error(
            "Could not find container div using XPath {} for page {}.".format(
                XPathStrings.DeputyInfoDiv, url))
        # return
    img = container.xpath(XPathStrings.ProfilePic)
    if img is None:
        logging.warning(
            "Could not parse image of the deputy from page at {}.".format(url))


def run(args):
    start_page = requests.get(args.start_url)
    page = html.fromstring(start_page.content)
    tbl = page.xpath(XPathStrings.DeputiesTableBody)

    if len(tbl) != 1:
        logging.error("Could not parse deputies table.")
        return
    tbl = tbl[0]
    df = parse_deputies_table(tbl)
    df = df[df.mandate == MandateType.Deputy]
    df.to_csv(args.save_deputy_list_to)


def parse_arguments():
    parser = ArgumentParser(description='Crawl deputy data')
    parser.add_argument(
        '--start-url',
        help="The URL of the page containing the list of deputies.",
        default="http://www.cdep.ro/pls/parlam/structura2015.ab?idl=1")
    parser.add_argument(
        '--save-deputy-list-to',
        help="The path of the CSV file where to save the deputy list.",
        default="./deputy-list.csv")
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
    run(args)
    parser = MandateInfoParser(
        url=
        'http://www.cdep.ro/pls/parlam/structura2015.mp?idm=173&leg=2004&cam=2',
        name='Stanciu Anghel',
        start_date=2004,
        end_date=2008)
