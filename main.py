import pymongo
import os
from vio_scraper import scrape, ItemNotFound
from dotenv import load_dotenv

from pprint import pprint

from typing import List, Dict, Tuple

load_dotenv()

item_list = [
    "Korrelite",
    "Gellium",
    "Axnit",
    "Narcor",
    "Red Narcor",
    "Vexnium",
    "Water"
]


mongo = pymongo.MongoClient(os.getenv("MONGO_URI"))

def add_scan_to_database(items: dict):
    pprint(items)
    value = mongo.Vio.Items.find_one_and_update(
        {"_id": 0},
        {"$inc": {"count": 1}}
    )
    items["_id"] = value["count"]
    mongo.Vio.Items.insert_one(items)

print("Scraping...")


if __name__ == "__main__":
    while True:
        try:
            response = scrape(item_list)
            add_scan_to_database(response)
        except ItemNotFound as e:
            print(e)
            print("Retrying...")
    print("Done.")

