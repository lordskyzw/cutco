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