from bs4 import BeautifulSoup

import requests
import time
import logging
import threading as thr

USD = "USD"


def __build_url(city: str, adults: int = None, rooms: int = None, checkin_date: str = None,
                checkout_date: str = None, price_range_start: int = None, price_range_end: int = None) -> str:
    base_url: str = 'https://www.booking.com/searchresults.html?ss='
    base_url += city

    if checkin_date is not None:
        base_url += "&checkin=" + str(checkin_date)
    if checkout_date is not None:
        base_url += "&checkout=" + str(checkout_date)
    if adults is not None:
        base_url += "&group_adults=" + str(adults)
    if rooms is not None:
        base_url += "&no_rooms=" + str(rooms)
    if price_range_start is not None and price_range_end is not None:
        base_url += "&nflt=price%3D" + USD + "-" + str(price_range_start) + "-" + str(price_range_end) + "-1"

    base_url += "&group_children=0"

    logging.info(f"Built URL: {base_url}")

    return base_url


def __get_specific_info(property_url: str, property_name: str, properties_dict: {str: []}) -> None:
    headers = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                              'Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62'})
    response = requests.get(property_url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser')

    coords = __get__coords(soup)

    photo_link = __get_photo_link(soup)

    logging.debug(f"Property: {property_name}, Coords: {coords}, Photo link: {photo_link}")

    properties_dict[property_name].append((float(coords[0]), float(coords[1]), photo_link))


def __get__coords(soup: BeautifulSoup) -> (float, float):
    results = soup.findAll('a', {
        'id': 'hotel_sidebar_static_map',
    })

    coords: str = results.pop(0).__getattribute__('attrs')['data-atlas-latlng']
    split_coords = coords.split(',')

    return float(split_coords[0]), float(split_coords[1])


def __get_photo_link(soup: BeautifulSoup) -> str:
    photo = soup.find('img', {
        'class': 'hide'
    })

    return photo['src']


def __transform_response(response: {str: []}) -> [{str: str}]:
    transformed_response = []

    for name, (link, price, aux_infos) in response.items():
        transformed_response.append({
            "name": name,
            "link": link,
            "photo": aux_infos[2],
            "price": price,
            "x": aux_infos[0],
            "y": aux_infos[1],
        })

    return transformed_response


def get_stays(city: str, adults: int = None, rooms: int = None, checkin_date: str = None, checkout_date: str = None,
              price_range_start: int = None, price_range_end: int = None) -> [{str: {str: str}}]:
    start_time = time.time()

    url = __build_url(city, adults, rooms, checkin_date, checkout_date, price_range_start, price_range_end)
    headers = ({'user-agent': 'mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) ' +
                              'chrome/96.0.4664.110 safari/537.36 edg/96.0.1054.62'})
    logging.error(f"URL: {url}")
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser')

    logging.error(f"THIS IS THE SOUP: {soup}")

    titles_raw = soup.findAll('div', {
        'data-testid': 'title'
    })
    titles = [result.get_text() for result in titles_raw]

    links_raw = soup.findAll('a', {
        'data-testid': 'title-link'
    })
    links = [individual_page['href'] for individual_page in links_raw]

    prices_raw = soup.findAll('span', {
        'data-testid': 'price-and-discounted-price'
    })
    prices = [price.get_text().strip() for price in prices_raw]

    response = {}
    for name, link, price in zip(titles, links, prices):
        response[name] = [link, price]

    threads = []
    for name, (link, price) in response.items():
        t = thr.Thread(target=__get_specific_info, args=(link, name, response))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    logging.debug(f"Got stays for {city} in {time.time() - start_time} seconds")

    return __transform_response(response)
