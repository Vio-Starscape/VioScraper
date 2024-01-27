import pymongo
import os
import logging
import time
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

config = {
    "search": [839, 50],
    "search_color": [70, 72, 74],
    "play_button": [305, 704],
    "play_button_color": [0, 159, 100],
    "starscape_button": [950, 556],
    "starscape_logo": [964, 451],
    "starscape_color": [240, 216, 95],
    "starscape_health": [917, 986],
    "starscape_health_color": [20, 180, 20],
}

mongo = pymongo.MongoClient(os.getenv("MONGO_URI"))

def add_scan_to_database(items: dict):
    pprint(items)
    value = mongo.Vio.Items.find_one_and_update(
        {"_id": 0},
        {"$inc": {"count": 1}}
    )
    items["_id"] = value["count"]
    mongo.Vio.Items.insert_one(items)

# if __name__ == "__main__":
#     from PIL import Image
#     import numpy as np
#     tab = TableExtraction()
#     # starscraper = ItemScraper(tab)
#     print(tab.extract_table("merged_image.png"))

#     # original = np.array(Image.open("test0.png"))
#     # buys = np.array(Image.open("test1.png"))
#     # sells = np.array(Image.open("test2.png"))
#     # img = Image.fromarray(starscraper.merge_screenshot(original, sells, buys))
#     # img.save("merged_image.png")

if __name__ == "__main__":
    while True:
        try:
            broken = False
            with ProcessManager(os.getenv("ROBLOX_GAME_PATH"), config) as process:
                starscraper = ItemScraper()
                while True:
                    try:
                        start = time.perf_counter()
                        resp = starscraper.better_scrape(item_list)
                        print(resp)
                        add_scan_to_database(resp)
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


