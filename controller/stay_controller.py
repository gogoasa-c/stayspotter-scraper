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
    checkin_date = request.json['checkin']
    checkout_date = request.json['checkout']

    response = stay_service.get_stays(city, adults, rooms, checkin_date, checkout_date)
    logging.info(f"Returning response: {response}")

    return jsonify(response)
