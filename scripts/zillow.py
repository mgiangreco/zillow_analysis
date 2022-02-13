from lxml import html
import requests
import unicodecsv as csv
import argparse
import json
from urllib.request import Request, urlopen
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
import time
from random import randint
from lxml.html import fromstring
from itertools import cycle
import traceback
import os
from datetime import datetime

options = Options()
ua = UserAgent()

def clean(text):
    if text:
        return ' '.join(' '.join(text).split())
    return None


def get_headers():
    # Creating headers.
    headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
               'accept-encoding': 'gzip, deflate, sdch, br',
               'accept-language': 'en-GB,en;q=0.8,en-US;q=0.6,ml;q=0.4',
               'cache-control': 'max-age=0',
               'upgrade-insecure-requests': '1',
               'user-agent': ua['google chrome']}
    return headers


def create_url(page_number):

    url = 'https://www.zillow.com/manhattan-new-york-ny/?searchQueryState={"pagination":{"currentPage":%d},"mapBounds":{"west":-75.27962761311436,"east":-73.38448601155186,"south":40.370587973413784,"north":40.922827615664026},"mapZoom":9,"regionSelection":[{"regionId":12530,"regionType":17}],"isMapVisible":true,"filterState":{"price":{"min":1500000,"max":2000000},"mp":{"min":681,"max":2384},"beds":{"min":2}},"isListVisible":true}' % int(page_number)
    print(url)
    return url


def save_to_file(response):
    # saving response to `response.html`

    with open("response.html", 'w') as fp:
        fp.write(response.text)


def write_data_to_csv(data):
    todays_date = datetime.now().strftime("%Y%m%d")
    # saving scraped data to csv.
    try:
        os.mkdir("./data/")
    except OSError as e:
        print("Directory exists")

    filename = "./data/%s" % (todays_date) + "properties-nyc.csv"

    with open(filename, 'ab') as csvfile:
        fieldnames = ['zpid', 'title', 'address', 'city', 'state', 'postal_code', 'price', 'bedrooms', 'bathrooms', 'area', 'real estate provider', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if os.stat(filename).st_size == 0:
            writer.writeheader()  # file doesn't exist yet, write a header

        for row in data:
            writer.writerow(row)


def get_response(url):
    # Getting response from zillow.com.

    for i in range(5):
        print("Request #%d"%i)
        try:
            response = requests.get(url)
            print("status code received:", response.status_code)
            if response.status_code != 200:
                # saving response to file for debugging purpose.
                save_to_file(response)
                continue
            else:
                save_to_file(response)
                return response
        except:
            print("Skipping. Connnection error")
    return None

def get_data_from_json(raw_json_data):
    # getting data from json (type 2 of their A/B testing page)

    #print(json.dumps(raw_json_data, indent=2))
    cleaned_data = clean(raw_json_data).replace('<!--', "").replace("-->", "")
    properties_list = []

    try:
        json_data = json.loads(cleaned_data)
        #print(json.dumps(json_data, indent=2))
        search_results = json_data.get('cat1').get('searchResults').get('listResults', [])
        #print(json.dumps(search_results, indent=2))

        for properties in search_results:
            property_info = properties.get('hdpData', {}).get('homeInfo')
            zpid = property_info.get('zpid')
            address = property_info.get('streetAddress')
            city = property_info.get('city')
            state = property_info.get('state')
            postal_code = property_info.get('zipcode')
            price = properties.get('price')
            bedrooms = properties.get('beds')
            bathrooms = properties.get('baths')
            area = properties.get('area')
            broker = properties.get('brokerName')
            property_url = properties.get('detailUrl')
            title = properties.get('statusText')

            data = {'zpid': zpid,
                    'address': address,
                    'city': city,
                    'state': state,
                    'postal_code': postal_code,
                    'price': price,
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'area': area,
                    'real estate provider': broker,
                    'url': property_url,
                    'title': title}
            properties_list.append(data)

        return properties_list

    except ValueError:
        print("Invalid json")
        return None


def parse(page_number):
    url = create_url(page_number)
    response = get_response(url)

    if not response:
        print("Failed to fetch the page, please check `response.html` to see the response received from zillow.com.")
        return None

    # These two new lines are added
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    webpage = urlopen(req).read()

    #replace the parser to take input added above
    #parser = html.fromstring(response.text)
    parser = html.fromstring(webpage)

    search_results = parser.xpath("//div[@id='search-results']//article")

    if not search_results:
        print("parsing from json data")
        # identified as type 2 page
        raw_json_data = parser.xpath('//script[@data-zrr-shared-data-key="mobileSearchPageStore"]//text()')
        return get_data_from_json(raw_json_data)

    print("parsing from html page")
    properties_list = []
    for properties in search_results:
        raw_zpid = properties.xpath(".//span[@itemprop='zpid']//span[@itemprop='zpid']//text()")
        raw_address = properties.xpath(".//span[@itemprop='address']//span[@itemprop='streetAddress']//text()")
        raw_city = properties.xpath(".//span[@itemprop='address']//span[@itemprop='addressLocality']//text()")
        raw_state = properties.xpath(".//span[@itemprop='address']//span[@itemprop='addressRegion']//text()")
        raw_postal_code = properties.xpath(".//span[@itemprop='address']//span[@itemprop='postalCode']//text()")
        raw_price = properties.xpath(".//span[@class='zsg-photo-card-price']//text()")
        raw_info = properties.xpath(".//span[@class='zsg-photo-card-info']//text()")
        raw_broker_name = properties.xpath(".//span[@class='zsg-photo-card-broker-name']//text()")
        url = properties.xpath(".//a[contains(@class,'overlay-link')]/@href")
        raw_title = properties.xpath(".//h4//text()")

        zpid = clean(raw_zpid)
        address = clean(raw_address)
        city = clean(raw_city)
        state = clean(raw_state)
        postal_code = clean(raw_postal_code)
        price = clean(raw_price)
        info = clean(raw_info).replace(u"\xb7", ',')
        broker = clean(raw_broker_name)
        title = clean(raw_title)
        property_url = "https://www.zillow.com" + url[0] if url else None
        is_forsale = properties.xpath('.//span[@class="zsg-icon-for-sale"]')

        properties = {'zpid': zpid,
                      'address': address,
                      'city': city,
                      'state': state,
                      'postal_code': postal_code,
                      'price': price,
                      'facts and features': info,
                      'real estate provider': broker,
                      'url': property_url,
                      'title': title}
        if is_forsale:
            properties_list.append(properties)
    return properties_list


if __name__ == "__main__":
    # Reading arguments
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    argparser.add_argument('page_number', help='')
    sortorder_help = """
    available sort orders are :
    newest : Latest property details,
    cheapest : Properties with cheapest price
    """

    argparser.add_argument('sort', nargs='?', help=sortorder_help, default='Homes For You')
    args = argparser.parse_args()
    page_number = args.page_number
    #sort = args.sort
    
    for i in range(1,26):
        time.sleep(randint(1,30))
        print ("Fetching data for page %s" % (i))
        scraped_data = parse(i)
        if scraped_data:
            print ("Writing data to output file")
            write_data_to_csv(scraped_data)
