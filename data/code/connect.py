import json
import sys
import time
import requests
from pymongo import MongoClient
import pymongo.errors
from pathlib import Path

BASE_URL = "https://api.manifold.markets"
REQUESTS_PER_MINUTE = 500
SECONDS_PER_MINUTE = 60
PAUSE_DURATION = SECONDS_PER_MINUTE / REQUESTS_PER_MINUTE

# Access credentials from a JSON file directly
def get_credentials():
    config_path = Path(__file__).parent / '../../config/client.json'
    with config_path.open('r') as f:
        credentials = json.load(f)
    return credentials['username'], credentials['pwd'], credentials['hostname'], credentials['port']

# Return a pymongo client connected to the Manifold database
def db_connect():
    username, pwd, hostname, port = get_credentials()
    try:
        client = MongoClient(f'mongodb://{username}:{pwd}@{hostname}:{port}')
        print("Connected to MongoDB")
        client.server_info()  # Will cause an exception if connection cannot be established
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)
    return client

# Return a collection from the Manifold database
def get_collection(collection_name):
    dbname = "manifoldDB"
    client = db_connect()
    db = client[dbname]
    collection = db[collection_name]
    return collection, client

def fetch_data_from_api(endpoint, params=None):
    try:
        start_time = time.time()  # start time
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()  #
        # Calculate actual pause needed, considering processing time
        actual_pause = max(0, PAUSE_DURATION - (time.time() - start_time))
        time.sleep(actual_pause)
        return response.json()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None
    
def ensure_unique_index(collection):
    # create a unique index on the 'id' field to prevent duplicates
    collection.create_index([("id", pymongo.ASCENDING)], unique=True)

def upsert_documents(collection, documents):
    for doc in documents:
        # The upsert=True option ensures that if the document does not exist, it is created
        collection.update_one({'id': doc['id']}, {'$set': doc}, upsert=True)
    print(f"Upserted {len(documents)} documents into {collection.name}.")

def fetch_groups(collection):
    last_created_time = None
    more_data = True
    while more_data:
        if last_created_time:
            params = {'beforeTime': last_created_time}
        else:
            params = {}
        data = fetch_data_from_api("v0/groups", params)
        if data:
            upsert_documents(collection, data)
            last_created_time = data[-1]['createdTime']
        else:
            more_data = False

def fetch_markets(group_collection, markets_collection):
    groups_data = group_collection.find({})
    for group in groups_data:
        group_id = group['id']
        markets_data = fetch_data_from_api("v0/markets", {"groupId": group_id, "limit": 1000})
        if markets_data:
            for market in markets_data:
                market['groupId'] = group_id
            upsert_documents(markets_collection, markets_data)  # Use upsert here

def fetch_bets_and_comments(markets_collection, bets_collection, comments_collection):
    markets_data = markets_collection.find({})
    for market in markets_data:
        market_id = market['id']

        # Fetch and upsert bets
        bets_data = fetch_data_from_api("v0/bets", {"contractId": market_id, "limit": 500})
        if bets_data:
            for bet in bets_data:
                bet['marketId'] = market_id
            upsert_documents(bets_collection, bets_data)

        # Fetch and upsert comments
        comments_data = fetch_data_from_api("v0/comments", {"contractId": market_id, "limit": 500})
        if comments_data:
            for comment in comments_data:
                comment['marketId'] = market_id
            upsert_documents(comments_collection, comments_data)

def main():
    # Connect to MongoDB and get collections
    client = db_connect()
    db = client['manifoldDB']
    group_collection = db['groups']
    markets_collection = db['markets']
    bets_collection = db['bets']
    comments_collection = db['comments']

    # Ensure unique indexes
    ensure_unique_index(markets_collection)
    ensure_unique_index(bets_collection)
    ensure_unique_index(comments_collection)

    fetch_groups(group_collection)
    fetch_markets(group_collection, markets_collection)
    fetch_bets_and_comments(markets_collection, bets_collection, comments_collection)

    client.close()


if __name__ == "__main__":
    main()

