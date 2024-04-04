import hashlib
from pymongo import MongoClient
import os

mongo = MongoClient(os.environ.get("MONGO_URI")) 

def generate_token(tuckshop_id, phone_number, change_amount, current_time):
    '''Returns a token with the following format XY-01-Bg where:
    XY are the first and second letters found in the hexidigest
    az are the third and fourth integers found in the hexidigest
    B is constant indicating tuckshop of origin, in this case tuckshop B
    g is the first lowercase letter found in the hexidigest'''
    hasher = hashlib.sha256()
    token_string = f"{tuckshop_id}{phone_number}{change_amount}{current_time}"
    hasher.update(token_string.encode('utf-8'))
    hash_256 = hasher.hexdigest()
    token_id = hash_256[:2].upper() + hash_256[2:4] + '-B' + hash_256[4:5]
    return token_id

def store_token(token_id, token_info):
    try:
        mongo.db.tokens.insert_one({'token_id': token_id, 'token_info': token_info})
        return True
    except Exception as e:
        return False
    
def format_phone_number(phone_number):
    # Check if the phone number starts with '+263'
    if phone_number.startswith('+263'):
        return phone_number[1:]  # Remove the '+' and return

    # Check if the phone number starts with '0'
    elif phone_number.startswith('0'):
        return '263' + phone_number[1:]  # Replace '0' with '263' and return

    # Check if the phone number starts with '263'
    elif phone_number.startswith('263'):
        return phone_number  # Return as it is

    # If none of the above, return the original phone number or handle as error
    else:
        return "invalid phone number"