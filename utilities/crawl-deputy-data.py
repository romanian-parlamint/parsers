from argparse import ArgumentParser
import requests
import logging
from lxml import etree, html
import pandas as pd


class XPathStrings:
    DeputiesTable = "//div[@class='grup-parlamentar-list grupuri-parlamentare-list']/table"
    DeputiesTableBody = "//div[@class='grup-parlamentar-list grupuri-parlamentare-list']/table/tbody"
    TableRow = ".//tr"
    RowColumn = ".//td"


def get_element_text(element):
    return ''.join(element.itertext())


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
        'row_num': [],
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
        data['row_num'].append(deputy_num)
        data['name'].append(deputy_name)
        data['period'].append(period_text)
        data['mandate'].append(mandate_text)
        data['period_link'].append(href)
    logging.info("Finished parsing deputies table.")
    records = pd.DataFrame.from_dict(data)
    print(records)
    return records


def run(args):
    start_page = requests.get(args.start_url)
    page = html.fromstring(start_page.content)
    tbl = page.xpath(XPathStrings.DeputiesTableBody)

    if len(tbl) != 1:
        logging.error("Could not parse deputies table.")
        return
    tbl = tbl[0]
    df = parse_deputies_table(tbl)


def parse_arguments():
    parser = ArgumentParser(description='Crawl deputy data')
    parser.add_argument(
        '--start-url',
        help="The URL of the page containing the list of deputies.",
        default="http://www.cdep.ro/pls/parlam/structura2015.ab?idl=1")
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
