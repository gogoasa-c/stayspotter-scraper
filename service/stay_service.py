from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import nltk
import requests
import time
import logging
import re
import threading as thr

USD = "USD"
RON = "RON"

nltk.download('punkt')


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
        base_url += "&nflt=price%3D" + RON + "-" + str(price_range_start) + "-" + str(price_range_end) + "-1"

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
        
    logging.info(f"Built URL: {base_url}")
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
    return soup.find("img", {"class": "hide"})['src']


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
    
    __remove_duplicates(transformed_response, additional_stays)
    
    for stay in additional_stays:
        transformed_response.append(stay)

    return transformed_response

def __remove_duplicates(booking_stays: [{str: str}], airbnb_stays: [{str: str}]) -> [{str: str}]:
    booking_names = [stay["name"] for stay in booking_stays]
    airbnb_names = [stay["name"] for stay in airbnb_stays]
    
    similar_stay_names = find_similar_stays(booking_names, airbnb_names)
    
    for similar_stay in similar_stay_names:
        booking_stays_duplicate = [stay for stay in booking_stays if stay["name"] == similar_stay[0]]
        airbnb_stays_duplicate = [stay for stay in airbnb_stays if stay["name"] == similar_stay[1]]
        
        # logging.info("=====================================")
        # logging.info(booking_stays_duplicate)
        # logging.info(airbnb_stays_duplicate)
        # logging.info("=====================================")
        
        if int(''.join(filter(str.isdigit, booking_stays_duplicate[0]["price"]))) > int(''.join(filter(str.isdigit, airbnb_stays_duplicate[0]["price"]))):
            booking_stays.remove(booking_stays_duplicate[0])
        else:
            airbnb_stays.remove(airbnb_stays_duplicate[0])

def __preprocess_text(string):
    tokens = nltk.word_tokenize(string.lower())
    return ' '.join(tokens)

def __compute_cosine_similarity(string1, string2, vectorizer):
    string1 = __preprocess_text(string1)
    string2 = __preprocess_text(string2)
    tfidf_matrix = vectorizer.transform([string1, string2])
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return cosine_sim[0][0]

def find_similar_stays(booking_stay_list, airbnb_stay_list, threshold=0.7):
    vectorizer = TfidfVectorizer().fit([__preprocess_text(text) for text in booking_stay_list + airbnb_stay_list])
    similar_pairs = []
    for stay1 in booking_stay_list:
        for stay2 in airbnb_stay_list:
            similarity_score = __compute_cosine_similarity(stay1, stay2, vectorizer)
            if similarity_score > 0.0:
                logging.info(f"Similarity between {stay1} and {stay2} is {similarity_score}")
            if similarity_score > threshold:
                similar_pairs.append((stay1, stay2, similarity_score))
    return similar_pairs

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
    print("link: ", url)
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

    images_raw = soup.findAll('img', {
        'data-testid': 'image'
    })
    
    images = [image['src'] for image in images_raw]

    thread.join()

    logging.info(f"For airbnb stays got {len(airbnb_stays)} stays in {time.time() - start_time} seconds")

    logging.info(airbnb_stays[0])
    
    response = {}
    for name, link, price, image in zip(titles, links, prices, images):
        response[name] = [link, price, (0, 0, image)]

    # threads = []
    # for name, (link, price) in response.items():
        # t = thr.Thread(target=__get_specific_info, args=(link, name, response))
    #     threads.append(t)
    #     t.start()
    # for t in threads:
    #     t.join()

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

def check_stay_availability(stay_url, initial_price):
    if "booking.com" in stay_url:
        return check_stay_availability_booking(stay_url, initial_price)
    
    if "airbnb.com" in stay_url:
        return check_stay_availability_airbnb(stay_url, initial_price)
    
    return {"error": "Something went wrong"}

def check_stay_availability_booking(stay_url, initial_price):
    headers = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                              'Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62'})
    
    
    response = requests.get(stay_url, headers=headers)

    availability_response = {}

    soup = BeautifulSoup(response.content, "html.parser")
    stay_cards = soup.findAll('div', {
        'id': 'no_availability_msg'
    })

    availability_response['available'] = len(stay_cards) == 0 

    prices = soup.findAll('span', {
        "class": "prco-valign-middle-helper"
    })
    if len(prices) == 0:
        availability_response['priceChanged'] = False
        return availability_response
        
    prices_text = [price.get_text() for price in prices]
    price_raw = prices_text[0]
    price = int(''.join(filter(str.isdigit, price_raw)))
    availability_response['priceChanged'] = price != initial_price
    
    return availability_response

def check_stay_availability_airbnb(stay_url, initial_price):
    headers = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                              'Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62'})
    
    driver = webdriver.Chrome()
    
    driver.get(stay_url)
    
    soup = None
    
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="_ati8ih"]'))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        driver.quit()
    except Exception as e:
        print(e)
        driver.quit()

    availability_response = {}

    
    stay_cards = soup.findAll('div', {
        'id': 'bookItTripDetailsError'
    })
    
    availability_response['available'] = len(stay_cards) == 0

    if availability_response['available'] == False:
        availability_response['priceChanged'] = False
        return availability_response

    prices = soup.findAll('span', {
        "class": "_j1kt73"
    })
    
    prices_text = [price.get_text() for price in prices]
    price_raw = prices_text[1]
    print(price_raw)
    price = int(''.join(filter(str.isdigit, price_raw)))
    print(price)
    availability_response['priceChanged'] = price != initial_price
    
    return availability_response