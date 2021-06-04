import pandas as pd
import requests
from urllib.parse import urljoin
from lxml import etree, html
from common import Resources, StringFormatter
from common import get_element_text


def load_deputy_list(file_name='./deputy-list.csv'):
    df = pd.read_csv(file_name)
    df = df.drop_duplicates(subset=['name'])

    print(df)
    return df


def split_name(name_parts):
    for part in name_parts:
        part = part.replace('-', ' ')
        for subpart in part.split():
            yield subpart.strip().upper()


MALE_SPECIFIC = ['HORIA', 'MIRCEA', 'ATTILA']
FEMALE_SPECIFIC = ['CARMEN']


def get_gender(name_parts):
    for part in split_name(name_parts):
        if part in FEMALE_SPECIFIC:
            return 'F'
        if part in MALE_SPECIFIC:
            return 'M'
        if part[-1] == 'A':
            return 'F'
    return 'M'


def parse_names(html_root):
    formatter = StringFormatter()

    name_element = html_root.xpath(DEPUTY_NAME_XPATH)
    name_element = name_element[0]
    first_name_parts, last_name_parts = [], []
    text = get_element_text(name_element)
    text = formatter.normalize(text)
    for part in text.split():
        if part.isupper():
            last_name_parts.append(part)
        else:
            first_name_parts.append(part)
    return ' '.join(first_name_parts), ' '.join(last_name_parts), get_gender(
        first_name_parts)


def parse_profile_picture(html_root, base_url):
    img = html_root.xpath(PROFILE_PICTURE_XPATH)
    if (img is None) or (len(img) == 0):
        return None
    for i in img:
        src = i.get('src')
        if src is not None:
            return urljoin(base_url, src)

    return None


def save_records(records, file_name='deputy-names-and-gender.csv'):
    data = pd.DataFrame.from_dict(records)
    data.to_csv(file_name)


BASE_URL = 'http://www.cdep.ro'
DEPUTY_NAME_XPATH = "//div[@class='boxTitle']/h1"
PROFILE_PICTURE_XPATH = "//div[@class='profile-pic-dep']/*/img"
df = load_deputy_list()
records = {'first_name': [], 'last_name': [], 'gender': [], 'image_url': []}
failed_urls = {'url': []}
count = 0
for row in df.itertuples():
    url = urljoin(BASE_URL, row.period_link)
    print("Request [{}/{}]. Loading data from URL {}.".format(
        count, len(df), url))
    try:
        response = requests.get(url)
        html_root = html.fromstring(response.content)
        first_name, last_name, gender = parse_names(html_root)
        records['first_name'].append(first_name)
        records['last_name'].append(last_name)
        records['gender'].append(gender)
        records['image_url'].append(parse_profile_picture(html_root, BASE_URL))
        count = count + 1
        if count % 10 == 0:
            save_records(records)
    except Exception:
        print("Could not parse data from {}.".format(url))
        failed_urls['url'].append(url)
        save_records(failed_urls, 'failed-urls.csv')

data = pd.DataFrame.from_dict(records)
data.to_csv("deputy-names-and-gender.csv")
print("Done.")
