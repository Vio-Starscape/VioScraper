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
    resp = starscraper.new_complete_scrape()
    print(resp)
    # add_scan_to_database(resp)
    end = time.perf_counter()
    print("Time taken: ", end - start)
    return resp

def main(config: dict):
    while True:
        try:
            broken = False
            with ProcessManager(os.getenv("ROBLOX_GAME_PATH"), config) as process:
                starscraper = ItemScraper(config)
                while True:
                    try:
                        start = time.perf_counter()
                        resp = starscraper.new_complete_scrape()
                        add_scan_to_database(resp)
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

    time.sleep(3)
    print(test_function(config))
    # print(test_function(config))