import logging

import service.stay_service as stay_service

from flask import Blueprint, request, jsonify

ss_blueprint = Blueprint('stay_spotter', __name__)


@ss_blueprint.route('/stays', methods=['POST'])
def get_stays():
    logging.info(f"Received request: {request.json}")

    city = request.json['city']
    adults = request.json['adults']
    rooms = request.json['rooms']
    checkin_date = request.json['checkIn']
    checkout_date = request.json['checkOut']
    price_range_start = request.json.get('priceRangeStart')
    price_range_end = request.json.get('priceRangeEnd')
    # price_range_start = request.json['priceRangeStart']
    # price_range_end = request.json['priceRangeEnd']

    response = stay_service.get_stays(city, adults, rooms, checkin_date, checkout_date,
                                      price_range_start, price_range_end)

    logging.info(f"Returning response: {response}")

    return jsonify(response)
