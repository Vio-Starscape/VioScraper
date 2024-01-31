import os
import logging
import time
import datetime
import toml
import requests
import json
from dotenv import load_dotenv
from vio_scraper import ProcessManager, ItemScraper, ItemNotFound

load_dotenv(override=True)

logger = logging.getLogger("LucaScraper")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
form = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
console_handler.setFormatter(form)
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

item_list = [
    "Korrelite",
    "Gellium",
    "Axnit",
    "Reknite",
    "Narcor",
    "Red Narcor",
    "Vexnium",
    "Water",
    "Polaris",
    "Adamant",
    "Ancient Composite Armor",
    "Ancient Coilgun-M",
    "Adv. drone core",
    "Ethereal (Barracuda)",
    "Loxodon"
]

cached = []

def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def add_scan_to_database(items: dict):
    try:
        print("Adding to database")
        cached.append(items)
        for item in cached:
            res = requests.post(
                os.getenv("URL"),
                json=json.loads(json.dumps(item, default=datetime_handler))
            )
            print(res.status_code)
            print(res.text)
        cached.clear()
    except Exception as e:
        print(e)


def test_function(config: dict):
    starscraper = ItemScraper(config)
    start = time.perf_counter()
    resp = starscraper.better_scrape(item_list)
    print(resp)
    # add_scan_to_database(resp)
    end = time.perf_counter()
    print("Time taken: ", end - start)


def main(config: dict):
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
                    except ItemNotFound as e:
                        print(e)
                        break
            if broken:
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)

if __name__ == "__main__":
    with open("config1080p.toml", "r") as f:
        config = toml.load(f)

    # from PIL import Image
    # from pyautogui import screenshot
    # from vio_scraper import ImageProcessing

    # # print(config)
    # imgproc = ImageProcessing()
    # t = ItemScraper(config)
    # img = Image.fromarray(t.take_screenshot_of_region("item_list"))
    # for j in range(t.getItemDepth()):
    #     chosen_item = img.crop([n+(j*37) if i%2 == 1 else n for i, n in enumerate(config["item_list_name"])])
    #     print(imgproc.get_item_name(chosen_item))
    # # chosen_item.show()
    # # print(imgproc.get_item_name(chosen_item))
    

    test_function(config)
