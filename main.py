import os
import logging
import time
import datetime
import toml
import requests
import keyboard
import json
from dotenv import load_dotenv
from vio_scraper import ProcessManager, ItemScraper, ItemNotFound, RAM

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
        bad = False
        for item in cached:
            if len(item["items"]) < 100:
                continue
            res = requests.post(
                os.getenv("URL"),
                json=json.loads(json.dumps(item, default=datetime_handler))
            )
            if res.status_code != 200:
                bad = True
                print(res.text)
        if not bad:
            cached.clear()
    except Exception as e:
        print(e)

def test_function(config: dict):
    starscraper = ItemScraper(config)
    start = time.perf_counter()
    resp = starscraper.new_complete_scrape()
    print(resp)
    add_scan_to_database(resp)
    end = time.perf_counter()
    print("Time taken: ", end - start)
    return resp

def main(config: dict):
    memory = {}
    while True:
        try:
            broken = False
            with RAM(os.getenv("DISCORD_WEBHOOK_URI"), os.getenv("RAM_PASSWORD"), os.getenv("RAM_URL"), config) as process:
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
                        if process.current_account not in memory:
                            memory[process.current_account] = 1
                        else:
                            memory[process.current_account] += 1
                        if memory[process.current_account] >= 2:
                            process.mark_account_as_yoinked(process.current_account)
                        break
                    if keyboard.is_pressed("q"):
                        broken = True
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

    main(config)
    # time.sleep(5)
    # test_function(config)
