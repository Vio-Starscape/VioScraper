import pymongo
import os
import logging
import time
import toml
from dotenv import load_dotenv
from pprint import pprint
from vio_scraper import ProcessManager, ItemScraper

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL + 1)
console_handler = logging.StreamHandler()
form = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
console_handler.setFormatter(form)
console_handler.setLevel(logging.CRITICAL + 1)

load_dotenv()

item_list = [
    "Korrelite",
    "Gellium",
    "Axnit",
    "Reknite",
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

if __name__ == "__main__":
    with open("config1080p.toml", "r") as f:
        config = toml.load(f)

    while True:
        try:
            broken = False
            with ProcessManager(os.getenv("ROBLOX_GAME_PATH"), config) as process:
                starscraper = ItemScraper(config)
                while True:
                    try:
                        start = time.perf_counter()
                        resp = starscraper.better_scrape(item_list)
                        print(resp)
                        # add_scan_to_database(resp)
                        end = time.perf_counter()
                        print("Time taken: ", end - start)
                    except KeyboardInterrupt:
                        broken = True
                        break
            if broken:
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)


