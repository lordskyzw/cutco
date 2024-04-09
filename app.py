from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from utils import generate_token, store_token, remove_token, store_ledger, get_last_ledger_entry, format_phone_number, token_info
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


@app.route('/tx', methods=['POST'])
def tx():
    # Extract data from the request
    data = request.json
    logging.info(f'Received data: {data}')
    phone_number = int(data.get('phone_number'))

    phone_number = format_phone_number(phone_number=phone_number)

    if phone_number=='invalid phone number':
        return f'Error:{phone_number}', 300
    
    change_amount = data.get('amount')
    current_time = datetime.datetime.now()
    logging.info(f'Creating token for {phone_number} with change amount of {change_amount} at {current_time}')

    # Generate the token
    token_id = generate_token(tuckshop_id=TUCKSHOP_ID, phone_number=phone_number, change_amount=change_amount, current_time=current_time)
  
    token_info = {
        'token_id': token_id,
        'date': current_time,
        'change_amount': change_amount,
        'tuckshop_id': TUCKSHOP_ID,
        'confirmation_key': random.choice(string.ascii_uppercase),
        'type': 'credit',
    }
    logging.info(f'Token generated: {token_id}')

    store_token(token_id=token_id, token_info=token_info)
    new_balance = store_ledger(phone_number=phone_number, transaction=token_info)

    if type(new_balance)==float:
        client.send_sms(source_number="$cutcoin", destination_number=phone_number, message=f'You have received: ${change_amount}USD\nFrom TuckShop: {TUCKSHOP_ID}\nNew cutcoin balance: ${new_balance} USD')
        logging.info(f'Token created: {token_id}')
        return jsonify({'tx_hash': token_id, 'tx_info': token_info, 'new_balance': new_balance}), 201
    
    else:
        return "Internal Server Error",500

@app.route('/use_change', methods=['POST'])
def redeem_token():
    '''
    this endpoint should first check if the user has enough balance to redeem the amount provided here is how it does it:
    1) by checking the balance from the users mongo ledgers collection  (search by phone number)
    2) it compares the balance with the amount provided in the request if the balance is greater
    if so, it proceeds to deduct from the users balance (perfom the debit_transaction) and delete the token (token_id should be found in the ledger document)
    if not, it should return an error message(insufficient balance)
    '''
    phone_number = request.json.get('phone_number')
    amount = request.json.get('amount')

    # Find the balance from the ledgers collection so edit this line
    last_ledger_entry = get_last_ledger_entry(phone_number)
    old_balance = last_ledger_entry['balance']

    if old_balance < amount:
        logging.info(f'Insufficient balance: {old_balance}')
        return jsonify({'message': 'Insufficient balance', 'validated': False}), 400

    token_id = last_ledger_entry['transactions'][-1]['token_id']
    confirmation_key = random.choice(string.ascii_uppercase)
    # Prepare the debit transaction for the ledger
    debit_transaction = {
        'destroyed_token_id': token_id,
        'confirmation_key': confirmation_key,
        'date': datetime.datetime.now(),
        'amount': amount,  # amount is positive store_ledger will handle the sign
        'type': 'debit',
        'description': f'Redeemed change of ${amount} USD'
    }

    new_balance = store_ledger(phone_number, debit_transaction)

    logging.info(f'new ledger balance: {new_balance}')
    
    # Send confirmation SMS with the new balance
    client.send_sms(source_number="$cutcoin", destination_number=phone_number, message=f'You have used ${amount}USD at Tuckshop:{TUCKSHOP_ID}.\nNew cutcoin balance: ${new_balance}USD\nConfirmation key: {confirmation_key}')
    
    # Include the new balance in the JSON response
    return jsonify({'message': 'Token used successfully', 'confirmation_key': confirmation_key, 'new_balance': new_balance, 'validated': True}), 200

   




@app.route('/available_tokens', methods=['GET'])
def available_tokens():

    available_tokens = tokens_collection.find({}, {'_id': 0, 'token_id': 1, 'token_info': 1})

    return jsonify({'available_tokens': list(available_tokens)}), 200

@app.route('/get_tx', methods=['POST'])
def get_tx():
    data = request.json
    tx_hash = data.get('tx_hash')

    transaction = token_info(token_id=tx_hash)
    return jsonify(transaction), 200


@app.route('/text_technician', methods=['GET'])
def text_technician():

    client.send_sms(source_number=TUCKSHOP_ID, destination_number=technician_number, message='Tuckshop B machine needs maintenance')

    return jsonify({'message': 'Technician has been notified'}), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)