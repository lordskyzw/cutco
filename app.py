from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from utils import generate_token, store_token,  format_phone_number
import datetime
from chromastone import Chromastone
import logging
import os
import random
import string
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(level=logging.DEBUG)
technician_number = os.environ.get("TECHNICIAN_NUMBER") 
TUCKSHOP_ID = str(os.environ.get("TUCKSHOP_ID"))
chromastone_api_key = os.environ.get("CHROMASTONE_API_KEY")


mongo = MongoClient(host=os.environ.get("MONGO_URI"))
db = mongo["cutcoin"]
tokens_collection = db.tokens

app = Flask(__name__)
CORS(app)

client = Chromastone(chromastone_api_key)


@app.route('/create_token', methods=['POST'])
def create_token():
    # Extract data from the request
    data = request.json
    phone_number = data.get('phone_number')

    phone_number = format_phone_number(phone_number=phone_number)

    if phone_number=='invalid phone number':
        return f'Error:{phone_number}', 300
    
    change_amount = data.get('change_amount')
    current_time = datetime.datetime.now()
    logging.info(f'Creating token for {phone_number} with change amount of {change_amount} at {current_time}')

    # Generate the token
    token_id = generate_token(tuckshop_id=TUCKSHOP_ID, phone_number=phone_number, change_amount=change_amount, current_time=current_time)
  
    token_info = {
        'date': current_time,
        'phone_number': phone_number,
        'change_amount': change_amount,
        'tuckshop_id': TUCKSHOP_ID,
        'confirmation_key': random.choice(string.ascii_uppercase)

    }
    logging.info(f'Token generated: {token_id}')

    if store_token(token_id=token_id, token_info=token_info):
        client.send_sms(source_number="$cutcoin", destination_number=phone_number, message=f'You have received: ${change_amount}USD\nFrom TuckShop: {TUCKSHOP_ID}\nTokenID: {token_id}')
        logging.info(f'Token created: {token_id}')
        return jsonify({'token_id': token_id}), 201
    
    else:
        return "Internal Server Error",500

@app.route('/redeem_token', methods=['POST'])
def redeem_token():
    token_id = request.json.get('token_id')

    token_data = tokens_collection.find_one({'token_id': token_id})

    if token_data:
        # Extract the confirmation key from the token data
        confirmation_key = token_data['token_info']['confirmation_key']
        
        tokens_collection.delete_one({'token_id': token_id})

        logging.info(f'Token redeemed: {token_id}')

        client.send_sms(source_number="$cutcoin", destination_number=token_data['token_info']['phone_number'], message=f'Confirmation! Your change of ${token_data["token_info"]["change_amount"]}\n Show teller confirmation key {confirmation_key}')

        return jsonify({'message': 'Token used successfully', 'confirmation_key': confirmation_key, 'validated': True}), 200
    else:

        logging.info(f'Invalid token: {token_id}')
       
        return jsonify({'message': 'Invalid token', 'validated': False}), 400


@app.route('/available_tokens', methods=['GET'])
def available_tokens():

    available_tokens = tokens_collection.find({}, {'_id': 0, 'token_id': 1, 'token_info': 1})

    return jsonify({'available_tokens': list(available_tokens)}), 200


@app.route('/text_technician', methods=['GET'])
def text_technician():

    client.send_sms(source_number=TUCKSHOP_ID, destination_number=technician_number, message='Tuckshop B machine needs maintenance')

    return jsonify({'message': 'Technician has been notified'}), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)