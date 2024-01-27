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
    # "Loxodon"
]

# config = {
#     "rob_search": [839, 50],
#     "search_color": [70, 72, 74],
#     "play_button": [305, 704],
#     "play_button_color": [0, 159, 100],
#     "starscape_button": [950, 556],
#     "starscape_logo": [964, 451],
#     "starscape_color": [240, 216, 95],
#     "starscape_health": [917, 986],
#     "starscape_health_color": [20, 180, 20],
#     "search": [658, 758],
#     "first_row": [993, 333],
#     "open_item": [1228, 825],
#     "close_item": [1121, 254],
#     "first_sell_row": [860, 370],
#     "first_buy_row": [865, 600],
#     "item": [793, 247, 1127, 802],
#     "sell": [793, 368, 1127, 565],
#     "sell_wheel": [1112, 373],
#     "buy_wheel": [1112, 603],
#     "item_x": [1122, 254],
#     "buy": [793, 600, 1127, 795],
#     "volume": [1008, 324, 1117, 341],
#     "switch_to_sell": [707, 276],
#     "switch_to_buy": [957, 276],
#     "name": [793, 254, 1033, 269]
# }

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


