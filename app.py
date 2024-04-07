from flask import Flask, request, jsonify
from pymongo import MongoClient
from utils import generate_token, store_token,  format_phone_number
import datetime
from chromastone import ChromaStone
import logging
import os

logging.basicConfig(level=logging.DEBUG)
technician_number = os.environ.get("TECHNICIAN_NUMBER") 
TUCKSHOP_ID = str(os.environ.get("TUCKSHOP_ID"))
chromastone_api_key = str(os.environ.get("CHROMASTONE_API_KEY"))

app = Flask(__name__)

client = ChromaStone(chromastone_api_key)
app.config["MONGO_URI"] = "mongodb://localhost:27017/tuckshopDB"
mongo = MongoClient(app.config["MONGO_URI"]) 

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

    # Generate the token
    token_id = generate_token(tuckshop_id=TUCKSHOP_ID, phone_number=phone_number, change_amount=change_amount, current_time=current_time)
  
    token_info = {
        'date': current_time,
        'phone_number': phone_number,
        'change_amount': change_amount,
        'tuckshop_id': TUCKSHOP_ID
    }

    if store_token(token_id=token_id, token_info=token_info):

        logging.info(f'Token created: {token_id}')
        return jsonify({'token_id': token_id}), 201
    
    else:
        return "Internal Server Error",500

@app.route('/redeem_token', methods=['POST'])
def redeem_token():
    token_id = request.json.get('token_id')

    token_data = mongo.db.tokens.find_one({'token_id': token_id})

    if token_data:
        
        mongo.db.tokens.delete_one({'token_id': token_id})

        logging.info(f'Token redeemed: {token_id}')

        client.send_sms(source_number=TUCKSHOP_ID, destination_number=token_data['token_info']['phone_number'], message=f'Your change of {token_data["token_info"]["change_amount"]} has been redeemed successfully')

        return jsonify({'message': 'Token used successfully', 'validated': True}), 200
    else:

        logging.info(f'Invalid token: {token_id}')
       
        return jsonify({'message': 'Invalid token', 'validated': False}), 400


@app.route('/available_tokens', methods=['GET'])
def available_tokens():

    available_tokens = mongo.db.tokens.find({}, {'_id': 0, 'token_id': 1, 'token_info': 1})

    return jsonify({'available_tokens': list(available_tokens)}), 200


@app.route('/text_technician', methods=['GET'])
def text_technician():

    client.send_sms(source_number=TUCKSHOP_ID, destination_number=technician_number, message='Tuckshop B machine needs maintenance')

    return jsonify({'message': 'Technician has been notified'}), 200