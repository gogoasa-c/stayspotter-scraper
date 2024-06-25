from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import requests
import time
import logging
import re
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

    # logging.info(f"Built URL: {base_url}")

    return base_url

def __build_url_airbnb(city: str, adults: int = None, rooms: int = None, checkin_date: str = None, checkout_date: str = None,
              price_range_start: int = None, price_range_end: int = None) -> str:
    if " " in city:
        city = city.replace(" ", "%20")
        
    base_url = f"https://www.airbnb.com/s/{city}/homes?"
    
    if adults:
        base_url += f"adults={adults}&"
    if rooms:
        base_url += f"min_bedrooms={rooms}&"
    if checkin_date:
        base_url += f"checkin={checkin_date}&"
    if checkout_date:
        base_url += f"checkout={checkout_date}&"
    if price_range_start:
        base_url += f"price_min={price_range_start}&"
    if price_range_end:
        base_url += f"price_max={price_range_end}&"
    return base_url


def __get_specific_info(property_url: str, property_name: str, properties_dict: {str: []}) -> None:
    headers = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                              'Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62'})
    response = requests.get(property_url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser')

    coords = __get__coords(soup)

    photo_link = __get_photo_link(soup)

    # logging.debug(f"Property: {property_name}, Coords: {coords}, Photo link: {photo_link}")

    properties_dict[property_name].append((float(coords[0]), float(coords[1]), photo_link))


def __get__coords(soup: BeautifulSoup) -> (float, float):
    results = soup.findAll('a', {
        'id': 'hotel_sidebar_static_map',
    })

    if (len(results) == 0):
        return 0, 0

    coords: str = results.pop(0).__getattribute__('attrs')['data-atlas-latlng']
    split_coords = coords.split(',')

    return float(split_coords[0]), float(split_coords[1])


def __get_photo_link(soup: BeautifulSoup) -> str:
    photo = soup.find('img', {
        'class': 'hide'
    })

    return photo['src']


def __transform_response(response: {str: []}, additional_stays: [{str: any}]) -> [{str: str}]:
    transformed_response = []

    for name, (link, price, aux_infos) in response.items():
        transformed_response.append({
            "name": name,
            "link": link,
            "photoUrl": aux_infos[2],
            "price": price,
            "x": aux_infos[0],
            "y": aux_infos[1],
        })
    
    for stay in additional_stays:
        transformed_response.append(stay)

    return transformed_response


def get_stays(city: str, adults: int = None, rooms: int = None, checkin_date: str = None, checkout_date: str = None,
              price_range_start: int = None, price_range_end: int = None) -> [{str: {str: str}}]:
    start_time = time.time()

    airbnb_stays = []
    
    thread = thr.Thread(target=get_stays_airbnb, args=(city, adults, rooms, checkin_date, checkout_date, price_range_start, price_range_end, airbnb_stays))
    thread.start()

    url = __build_url(city, adults, rooms, checkin_date, checkout_date, price_range_start, price_range_end)
    headers = ({'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'})
    # logging.error(f"URL: {url}")
    # response1 = requests.get(url, headers=headers)
    response = requests.get(url, headers=headers)

    # if response1 == response:
        # logging.error("THEY ARE EQUAL")

    soup = BeautifulSoup(response.content, 'html.parser')

    # logging.error(f"THIS IS THE SOUP: {soup}")

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

    thread.join()

    logging.info(f"For airbnb stays got {len(airbnb_stays)} stays in {time.time() - start_time} seconds")

    logging.info(airbnb_stays[0])
    
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

    logging.info(f"Got stays for {city} in {time.time() - start_time} seconds")
    # logging.debug(f'URL: {url}')
    return __transform_response(response, airbnb_stays)

def get_stays_airbnb(city: str, adults: int = None, rooms: int = None, checkin_date: str = None, checkout_date: str = None,
              price_range_start: int = None, price_range_end: int = None, stays: [{str: str}] = None): 
    url = __build_url_airbnb(city, adults, rooms, checkin_date, checkout_date, price_range_start, price_range_end)

    driver = webdriver.Chrome()
    
    driver.get(url)
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[itemprop="url"]'))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        driver.quit()
        
        cards = soup.findAll('meta', {
            'itemprop': 'url'
        })
        
        images = soup.findAll('img', {
            'data-original-uri': True,
            'style': lambda style: '--dls-liteimage-border-radius: 50%;' not in style
        })
        
        total_prices = soup.findAll('span', {
            'class': False
        }, string=re.compile(r'[\d,]+\slei\stotal'))
        
        titles = soup.findAll('meta', {
            'itemprop': 'name'
        })
        
        stay_info = [
            {
                'name': title["content"],
                'price': price.text.replace('\xa0', ' '),
                'photoUrl': image['src'],
                'link': f'https://{card["content"]}',
                'x': 0,
                'y': 0
            }
            for title, price, image, card in zip(titles, total_prices, images, cards)
        ]
        
        for stay in stay_info:
            stays.append(stay)
    except Exception as e:
        print(e)
        driver.quit()

def check_stay_availability(stay_url):
    headers = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                              'Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62'})
    response = requests.get(stay_url, headers=headers)

    soup = BeautifulSoup(response.content, "html.parser")
    stay_cards = soup.findAll('div', {
        'data-testid': 'property-card-container'
    })

    unavailable_stays = [card for card in stay_cards if "This property has no availability" in card.text]
    
    if len(unavailable_stays) > 0:
        return {"available": False}
    
    return {"available": True}