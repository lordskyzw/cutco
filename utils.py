import hashlib
from pymongo import MongoClient
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

mongo = MongoClient(host=os.environ.get("MONGO_URI"))
db = mongo["cutcoin"]
tokens_collection = db.tokens
ledgers_collection = db.ledgers

def generate_token(tuckshop_id, phone_number, change_amount, current_time):
    '''Returns a token with the following format XY-01-Bg where:
    XY are the first and second characters found in the hex digest.
    01 are the third and fourth integers found in the hex digest.
    B is a constant indicating tuckshop of origin, in this case tuckshop B.
    g is the first lowercase letter found in the hex digest.'''
    import hashlib
    import re
    
    # Create the hasher and generate the hash
    hasher = hashlib.sha256()
    token_string = f"{tuckshop_id}{phone_number}{current_time}{change_amount}"
    hasher.update(token_string.encode('utf-8'))
    hash_256 = hasher.hexdigest()
    
    # Extract the first two characters
    XY = hash_256[:2].upper()
    
    # Find the first two integers in the hash
    integers = re.findall('\d', hash_256)
    if len(integers) >= 5:
        digits = "".join(integers[2:4])
    else:
        digits = "00"  # Default if not enough integers are found

    # Find the first lowercase letter in the hash
    letters = re.findall('[a-z]', hash_256)
    if letters:
        g = letters[0]
    else:
        g = "a"  # Default if no lowercase letter is found

    # Assemble the token
    token_id = f"{XY}-{digits}-B{g}"
    return token_id

def store_token(token_id, token_info):
    try:
        tokens_collection.insert_one({'token_id': token_id, 'token_info': token_info})
        return True
    except Exception as e:
        return False

def remove_token(token_id):
    try:
        tokens_collection.delete({'token_id': token_id})
        return True
    except Exception as e:
        return False
    
def store_ledger(phone_number, transaction):
    """
    Update the ledger for a given phone number by adding a new transaction.
    If the ledger doesn't exist, create a new one.
    """
    try:

        query = {'phone_number': phone_number}

        update = {
            '$push': {'transactions': transaction},
            '$inc': {'balance': transaction['change_amount'] if transaction['type'] == 'credit' else -transaction['change_amount']}
        }
   
        result = ledgers_collection.update_one(query, update, upsert=True)

        if result.matched_count > 0 or result.upserted_id is not None:
            return True
        else:
            return False
    except Exception as e:
        return False

    
def get_last_ledger_entry(phone_number):
    try:
        # Retrieve the ledger document for the given phone number
        ledger_entry = ledgers_collection.find_one({'phone_number': phone_number})

        # Return the whole ledger entry as it contains the balance and all transactions
        return ledger_entry
    except Exception as e:
        print(f"An error occurred: {e}")
        return None  # It's better to return None than False to distinguish between an error and a missing entry

    
def format_phone_number(phone_number):
    '''
    returns phone number in the following example format: 263775123456
    in that it starts with 263 always and has 9 digits after that
    '''

    # Check if the phone number starts with '+263'
    if phone_number.startswith('+263') and len(phone_number) == 13:
        return phone_number[1:]  # Remove the '+' and return

    # Check if the phone number starts with '0'
    elif phone_number.startswith('0') and len(phone_number) == 10:
        return '263' + phone_number[1:]  # Replace '0' with '263' and return

    # Check if the phone number starts with '263'
    elif phone_number.startswith('263') and len(phone_number) == 12:
        return phone_number  # Return as it is

    # If none of the above, return the original phone number or handle as error
    else:
        return "invalid phone number"