from flask import Flask, request, jsonify, Response
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
    phone_number = data.get('phone_number')
    transaction_type = data.get('transaction_type')


    phone_number = format_phone_number(phone_number=phone_number)
    if transaction_type == 'deposit':

        if phone_number=='invalid phone number':
            return f'Error:{phone_number}', 300
        
        change_amount = float(data.get('amount'))
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
        logging.info(f'Token generated: {token_id}\n Token Info: {token_info}')

        store_token(token_id=token_id, token_info=token_info)
        new_balance = store_ledger(phone_number=phone_number, transaction=token_info) ### this is where the bug is
        logging.info(f"stored token and new balance is: {new_balance}")

        if type(new_balance)==float:
            client.send_sms(source_number="Cut Coin", destination_number=phone_number, message=f'You have received: ${change_amount}USD\nFrom TuckShop: {TUCKSHOP_ID}\nNew cutcoin balance: ${new_balance} USD')
            logging.info(f'Token created: {token_id}')
            return jsonify({'tx_hash': token_id, 'tx_info': token_info, 'new_balance': new_balance}), 201
        
        else:
            logging.info(f'new_balance is of type {type(new_balance)}')
            return "Internal Server Error",500
        
    elif transaction_type == 'withdrawal':
        amount = float(request.json.get('amount'))
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
        return jsonify({'message': f'Change of ${amount} USD used successfully', 'confirmation_key': confirmation_key, 'new_balance': new_balance, 'validated': True}), 200
    
    else:
        logging.error(f'invalid or missing transaction type')
        return jsonify({'message': f'invalid or missing transaction type: deposit or withdrawal'})


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
    amount = float(request.json.get('amount'))

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
    return jsonify({'message': f'Change of ${amount} USD used successfully', 'confirmation_key': confirmation_key, 'new_balance': new_balance, 'validated': True}), 200

   
@app.route('/buy_airtime', methods=['POST'])
def buy_airtime():
    '''this endpoint receives the traffic from africastalking and processes the airtime purchase'''
    data = request.form
    # we need to extract the received data
    session_id = request.values.get("sessionId", None)
    service_code = request.values.get("serviceCode", None)
    phone_number = format_phone_number(request.values.get("phoneNumber", None))
    text = request.values.get("text", "default")
    if text == "":
        response_text = "CON Welcome to hitcoin.\n"
        response_text += "1. Buy airtime\n"
        response_text += "2. Check balance\n"
        response_text += "3. Send hitcoin"
    
    elif text == "1":
        response_text = "CON Enter the amount you want to buy"
    elif text == "1*1":
        response_text = "CON Enter the phone number"
    elif text == "2":
        try:
            last_ledger_entry = get_last_ledger_entry(phone_number)
            old_balance = last_ledger_entry['balance']
            response_text = f"END Your balance is {str(old_balance)}"
        except Exception as e:
            response_text = f"END Your balance is 0"
    elif text == "3":
        response_text = "CON Enter the phone number"
    elif text == "3*1":
        response_text = "CON Enter the amount you want to send"

    
    # Create a response object with text/plain content type
    response = Response(response_text, content_type='text/plain')
    return response
    # #we then check if the phonenumber passed has enough balance to make the airtime purchase
    # last_ledger_entry = get_last_ledger_entry(phone_number) #this is the last entry in the ledger
    # old_balance = last_ledger_entry['balance']
    # if old_balance < amount:
    #     logging.info(f'Insufficient balance: {old_balance}')
    #     return jsonify({'message': 'Insufficient balance', 'validated': False}), 400
    # #if the user has enough balance we proceed to deduct the amount from the users balance
    # token_id = last_ledger_entry['transactions'][-1]['token_id']
    # confirmation_key = random.choice(string.ascii_uppercase)
    # # Prepare the debit transaction for the ledger
    # debit_transaction = {
    #     'destroyed_token_id': token_id,
    #     'confirmation_key': confirmation_key,
    #     'date': datetime.datetime.now(),
    #     'amount': amount,  # amount is positive store_ledger will handle the sign
    #     'type': 'debit',
    #     'description': f'Redeemed change of ${amount} USD'
    # }

    # new_balance = store_ledger(phone_number, debit_transaction)

    # logging.info(f'new ledger balance: {new_balance}')
    # #now we need to respond to the africastalking api with a success message
    # return jsonify({'message': f'Change of ${amount} USD used successfully', 'confirmation_key': confirmation_key, 'new_balance': new_balance, 'validated': True}), 200




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
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000), debug=True)