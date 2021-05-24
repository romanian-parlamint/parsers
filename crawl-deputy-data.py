from argparse import ArgumentParser
import requests
import logging
import re
import time
import random
from lxml import etree, html
import pandas as pd
from common import get_element_text
from common import OrganizationType
from urllib.parse import parse_qs, urljoin, urlparse
from collections import namedtuple
from datetime import date
from common import Resources, StringFormatter


class XPathStrings:
    DeputiesTableBody = "//div[@class='grup-parlamentar-list grupuri-parlamentare-list']/table/tbody"
    DeputyInfoDiv = "//div[@id='oldDiv']"
    ProfilePic = "//div[@class='profile-pic-dep']/a"
    InfoSections = "//div[@class='boxDep clearfix']"
    DeputyName = "//div[@class='boxTitle']/h1"


class MandateType:
    Deputy = 'deputat'
    Senator = 'senator'


Affiliation = namedtuple('Affiliation',
                         ['organization', 'start_date', 'end_date'])


class MandateInfoParser:
    """Parses the information from a page describing a deputy mandate.
    """
    def __init__(self, url, start_year, end_year=None):
        """Creates a new instance of MandateInfoParser.

        Parameters
        ----------
        url : str, required
            The url of the term/mandate page.
        start_year: int, required
            The start year of the term/mandate.
        end_year: int, optional
            The end year of the term/mandate. Default is None which means that the term is ongoing.
        """
        self.url = url
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
        self.formatter = StringFormatter()
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
        affiliation_section = self._find_affiliations_section()
        if affiliation_section is None:
            logging.error(
                "Could not find affiliations section for page '{}'.".format(
                    self.url))
            return []

        title = self._get_affiliation_title(affiliation_section)
        logging.info(
            "Title of the affiliations section for page '{}' is: '{}'.".format(
                self.url, title))
        info_table = next(affiliation_section.iterdescendants(tag='table'))
        affiliations = []
        for row in info_table:
            text = self.formatter.normalize(get_element_text(row))
            affiliations.append(self._parse_affiliation(text))

        return affiliations

    def parse_names(self):
        """Parses the first and last names of the deputy.

        Returns
        -------
        (first_name, last_name): tuple of str
            The tuple containing first and last names of the deputy.
        """
        name_element = self.html_root.xpath(XPathStrings.DeputyName)
        if name_element is None:
            logging.error(
                "Could not find the element containing deputy name in page '{}'."
                .format(self.url))
            return None, None
        name_element = name_element[0]
        first_name_parts, last_name_parts = [], []
        text = get_element_text(name_element)
        text = self.formatter.normalize(text)
        for part in text.split():
            if part.isupper():
                last_name_parts.append(part)
            else:
                first_name_parts.append(part)
        return ' '.join(first_name_parts), ' '.join(last_name_parts)

    def parse_profile_picture(self):
        """Retrieves the URL of the profile picture.

        Returns
        -------
        img_url: str
            The URL of the profile pictrure if found; otherwise None.
        """
        anchor_element = self.html_root.xpath(XPathStrings.ProfilePic)
        if anchor_element is None:
            logging.warning(
                "Could not parse the profile picture for page '{}'.".format(
                    self.url))
            return None
        anchor_element = anchor_element[0]
        return anchor_element.get('href')

    def _find_affiliations_section(self):
        """Iterates the HTML tree to find the section containing the affiliation info.

        Returns
        -------
        affiliation_section: etree.Element
            The HTML element containing affiliation info or None.
        """
        for elem in self.html_root.xpath(XPathStrings.InfoSections):
            for heading in elem.iterdescendants(tag='h3'):
                text = get_element_text(heading)
                text = self.formatter.normalize(text)
                if Resources.PoliticalParty in text or Resources.PoliticalGroup in text:
                    return elem

        logging.error(
            "Could not find the affiliation section for page '{}'.".format(
                self.url))
        return None

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
        (start_date, end_date): tuple of str
            The start and end dates of the affiliation in the format yyyy[-mm], i.e. the month part is optional.
            End date may be None meaning that the mandate is ongoing.
        """
        start_date = str(self.start_year)
        end_date = None
        if self.end_year is not None:
            end_date = str(self.end_year)
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
        dt: str
            The date parsed from the provided string or None.
        """
        logging.info(
            "Parsing affiliation date from string '{}'.".format(date_str))
        match = self.date_regex.search(date_str)
        if match is None:
            logging.info("Date regex did not match the provided string.")
            return None

        month = match.group(1).lower().strip('.')
        year = int(match.group(2))
        logging.info(
            "The following date parts were found: month={}, year={}.".format(
                month, year))
        return '-'.join([year, self.month_map[month]])

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


class DeputyAffiliationCrawler:
    """Iterates over the list of deputy mandate records and scrapps deputy info from pages.
    """
    def __init__(self, base_url, data_frame, max_sleep_interval=5):
        """Creates a new instance of DeputyAffiliationScrapper.

        Parameters
        ----------
        base_url : str, required
            The base URL from which to create URLs for mandate pages.
        data_frame : pandas.DataFrame, required
            The data frame containing the links to each mandate page.
        max_sleep_interval: int, optional
            The maximum interval to sleep between the requests.
        """
        self.base_url = base_url
        self.data_frame = data_frame
        self.org_name_regex = re.compile(r"(([A-Z]+\s+)-)(.+)", re.MULTILINE)
        self.max_sleep_interval = max_sleep_interval
        self.deputy_records = {}

    @property
    def deputy_info(self):
        """Returns a pandas.DataFrame containing the deputy records.
        """
        return pd.DataFrame.from_dict(self.deputy_records)

    def fetch_data(self, save_records=None):
        """Crawls the deputy and organization info from the links in the data frame.

        Parameters
        ----------
        save_records: callback, optional
            A callback method which receives a data frame of the records as the parameter and should write it to disk.
        """
        logging.info("Start crawling deputy and organizations info.")
        should_save = False
        for row in self.data_frame.itertuples():
            sleep_interval = random.randint(1, self.max_sleep_interval)
            logging.info(
                "Sleeping for {} seconds before sending the request.".format(
                    sleep_interval))
            time.sleep(sleep_interval)
            url = urljoin(self.base_url, row.period_link)
            try:
                self._fetch_records(url, row.period)
            except Exception as ex:
                logging.error(
                    "Could not parse mandate info from page {}.".format(url))
                logging.error(ex)
                self._add_record(-1, None, None, None, None, None, None, None,
                                 url)
                should_save = True
            should_save = should_save or (row.Index % 10 == 0)
            if should_save and (save_records is not None):
                logging.info("Saving records.")
                save_records(self.deputy_info)
                should_save = False

        logging.info("Crawling finished.")

    def _fetch_records(self, url, period):
        """Loads the deputy info records from the specified url and period.

        Parameters
        ----------
        url: str, required
            The URL of the page from which to retrieve records.
        period: str, required
            The period string containing start and end year of a mandate.
        """
        start_year, end_year = self._parse_mandate_period(period)
        if (end_year is not None) and (end_year < 2000):
            logging.info("Skipping period before 2000.")
            return

        logging.info(
            "Parsing mandate info from URL {} with start year={}, end year={}."
            .format(url, start_year, end_year))
        parser = MandateInfoParser(url, start_year, end_year)
        deputy_id = parser.parse_deputy_id()
        first_name, last_name = parser.parse_names()
        profile_pic = parser.parse_profile_picture()
        for affiliation_period in parser.parse_affiliations():
            org_name, acronym = self._split_organization_name(
                affiliation_period.organization)
            self._add_record(deputy_id, first_name, last_name, profile_pic,
                             org_name, acronym, affiliation_period.start_date,
                             affiliation_period.end_date, url)

    def _add_record(self, deputy_id, first_name, last_name, profile_picture,
                    organization, acronym, start_date, end_date, url):
        """Adds a records to the records collection.

        Parameters:
        deputy_id: int, required
            The id of the deputy.
        first_name: str, required
            The first name of the deputy.
        last_name: str, required
            The last name of the deputy.
        profile_picture: str, required
            The URL of the profile picture.
        organization: str, required
            The name of the organization to which deputy is affiliated.
        acronym: str, required
            The acronym of the organization.
        start_date: str, required
            The (partial) date of when the affiliation started.
        end_date: str, required
            The (partial) end date of when the affiliation ended. None means deputy is still affiliated.
        url: str, required
            The URL of the page from where the record was parsed.
        """
        if len(self.deputy_records) == 0:
            self.deputy_records['deputy_id'] = []
            self.deputy_records['first_name'] = []
            self.deputy_records['last_name'] = []
            self.deputy_records['profile_picture'] = []
            self.deputy_records['organization'] = []
            self.deputy_records['acronym'] = []
            self.deputy_records['start_date'] = []
            self.deputy_records['end_date'] = []
            self.deputy_records['url'] = []
        self.deputy_records['deputy_id'].append(deputy_id)
        self.deputy_records['first_name'].append(first_name)
        self.deputy_records['last_name'].append(last_name)
        self.deputy_records['profile_picture'].append(profile_picture)
        self.deputy_records['organization'].append(organization)
        self.deputy_records['acronym'].append(acronym)
        self.deputy_records['start_date'].append(start_date)
        self.deputy_records['end_date'].append(end_date)
        self.deputy_records['url'].append(url)

    def _split_organization_name(self, organization_name):
        """Splits the organization name into a tuple containing the name and the acronym.

        Parameters
        ----------
        organization_name: str, required
            The organization name to split.

        Returns
        -------
        (name, acronym): tuple of str
            The name and the acronym of the organization. If acronym cannot be identified it will be None.
        """
        match = self.org_name_regex.match(organization_name)
        if match is None:
            return organization_name, None
        acronym = match.group(2).strip()
        name = match.group(3).strip()
        return name, acronym

    def _parse_mandate_period(self, period):
        """Parses the period string and returns the start and end year of a mandate.

        Parameters
        ----------
        period: str
            The mandate period containing start and end years split by dash.

        Returns
        -------
        (start_year, end_year): tuple of int
            The start and end years of the period. For ongoing mandates the end year is None.
        """
        start, end = period.split('-')
        start_year = int(start)
        if end.lower() == Resources.PresentTime.lower():
            end_year = None
        else:
            end_year = int(end)
        return (start_year, end_year)


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


def get_base_url(url):
    """Returns the base URL from the provided URL string.

    Parameters
    ----------
    url: str
        The url from which to build the base URL.

    Returns
    -------
    base_url: str
        The base URL of the provided URL string.
    """
    parsed = urlparse(url)
    base_url = "{scheme}://{host}".format(scheme=parsed.scheme,
                                          host=parsed.hostname)
    return base_url


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
    logging.info("Finished parsing deputies table. Saving data to {}.".format(
        args.deputy_list_file))
    df.to_csv(args.deputy_list_file)

    base_url = get_base_url(args.start_url)
    crawler = DeputyAffiliationCrawler(base_url, df)
    crawler.fetch_data(lambda rec: rec.to_csv(args.deputy_info_file))
    logging.info("Saving data to disk.")
    deputy_info_df = crawler.deputy_info
    deputy_info_df.to_csv(args.deputy_info_file)
    logging.info("Deputy info saved to {}.".format(args.deputy_info_file))
    logging.info("That's all folks!")


def parse_arguments():
    parser = ArgumentParser(description='Crawl deputy data')
    parser.add_argument(
        '--start-url',
        help="The URL of the page containing the list of deputies.",
        default="http://www.cdep.ro/pls/parlam/structura2015.ab?idl=1")
    parser.add_argument(
        '--deputy-list-file',
        help="The path of the CSV file where to save the deputy list.",
        default="./deputy-list.csv")
    parser.add_argument(
        '--deputy-info-file',
        help="The path of the CSV file where to save deputy info.",
        default='./deputy-info.csv')
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
