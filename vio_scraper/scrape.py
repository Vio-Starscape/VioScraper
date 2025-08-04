import logging
import pydirectinput
import pyautogui
import numpy as np
import time
import keyboard
import multiprocessing
import sys
from queue import Queue
from threading import Thread, Event
from concurrent.futures import ProcessPoolExecutor
from PIL import ImageGrab, Image
from .extraction import ImageProcessing
from datetime import datetime, timezone

logger = logging.getLogger("LucaScraper")

class ItemNotFound(Exception):
    pass

def unknown_worker(data):
    img = ImageProcessing()
    try:
        info = img.extract_data_from_image(data["image"], data["extra_buy"], data["extra_sell"])
        return {
            "name": info["name"],
            "data": info
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

class ItemScraper:

    max_rows = 8
    table_scale = 2 # Upscale for orders
    row_height = 37

    def __init__(self, config: dict, model_path: str = None) -> None:
        self.config = config
        self.model_path = model_path
        self.processor = ImageProcessing()

    def grab_images(self, queue, config, stop_event):
        time.sleep(1)
        grab = ImageGrab.grab()
        # Figure out this logic because it will not work long term
        while (not keyboard.is_pressed("q")) and not stop_event.is_set()\
            and any([grab.getpixel((config["top_of_listing"][0], y)) == (255, 255, 255) for y in range(config["top_of_listing"][1], config["bottom_of_listing"][1]+20)]):
            time.sleep(0.1)
            pydirectinput.press("enter")
            time.sleep(0.1)
            self.click_at_location_name("open_item")
            # while ImageGrab.grab().getpixel(config["item_background"]) != (20, 20, 20) and not keyboard.is_pressed("q"):
            time.sleep(0.1)
            if not self.waitForItemLoad():
                raise ItemNotFound("Item not found")
            img, extra_sells, extra_buys = self.improvedScanItem()
            # Image.fromarray(img).save(f"unknown{count}.png")
            queue.put(
                {
                    "name": "unknown",
                    "extra_sell": extra_sells,
                    "extra_buy": extra_buys,
                    "image" : img
                }
            )
            self.closeItem()
            time.sleep(0.1)
            pydirectinput.press("down")
            time.sleep(0.1)
            grab = ImageGrab.grab()
        if keyboard.is_pressed("q"):
            return

    def process_images(self, queue, executor, current_iter, stop_event, cpus=8):
        images = []
        last_name = None
        repeat_count = 0
        while True:
            data = queue.get()
            if data is None:  # sentinel value to indicate end of processing
                break
            images.append(data)
            if len(images) == cpus:
                results = list(executor.map(unknown_worker, images))
                for result in results:
                    if result is None:
                        continue
                    if result["name"].endswith("tag"):
                        continue

                    if result["name"] == last_name:
                        repeat_count += 1
                    else:
                        last_name = result["name"]
                        repeat_count = 1

                    if repeat_count >= 20:
                        logger.info("Detected 20 times stopping loop!")
                        stop_event.set()
                        return

                    result["name"] = result["name"].replace(".", "")
                    if result["name"] not in current_iter["items"]:
                        current_iter["items"][result["name"]] = result["data"]
                    else:
                        # current_iter["items"][result["name"]]["buy"].extend(result["data"]["buy"])
                        # current_iter["items"][result["name"]]["buy"] = list(set(current_iter["items"][result["name"]]["buy"]))
                        current_iter["items"][result["name"]]["buy"] = result["data"]["buy"]
                        # current_iter["items"][result["name"]]["sell"].extend(result["data"]["sell"])
                        # current_iter["items"][result["name"]]["sell"] = list(set(current_iter["items"][result["name"]]["sell"]))
                        current_iter["items"][result["name"]]["sell"] = result["data"]["sell"]
                images = []

    def new_complete_scrape(self, location: str = "c1"):
        current_iter = {
            "location": location,
            "time_scanned": datetime.now(timezone.utc),
            "items": {}
        }
        pydirectinput.press("\\")
        pydirectinput.press("right")
        pydirectinput.press("left")
        pydirectinput.press("left")
        pydirectinput.press("down")
        # for _ in range(5):
        #     pydirectinput.press("left")
        cpus = multiprocessing.cpu_count()
        queue = Queue()

        stop_event = Event()

        with ProcessPoolExecutor(max_workers=cpus) as executor:
            grabber = Thread(target=self.grab_images, args=(queue, self.config, stop_event))
            processor = Thread(target=self.process_images, args=(queue, executor, current_iter, stop_event, cpus))
            grabber.start()
            processor.start()
            grabber.join()
            queue.put(None)  # signal to processor that grabbing is done
            processor.join()
        # self.click_at_location_name("open_item")
        pydirectinput.press("\\")
        self.click_at_location_name("first_row")
        self.click_at_location_name("Armor")
        time.sleep(0.5)
        self.click_at_location_name("All")
        time.sleep(0.5)
        self.click_at_location_name("Resources")
        time.sleep(0.5)
        self.click_at_location_name("All")

        for _ in range(5):
            time.sleep(0.1)
            pydirectinput.press("\\")
            # time.sleep(0.1)
            # self.click_at_location_name("terminal_x")
            # time.sleep(0.1)
            # pydirectinput.press("f")
            time.sleep(0.1)
            pydirectinput.press("\\")
            time.sleep(0.1)
        if len(current_iter["items"]) < 100:
            raise ItemNotFound("No items found")
        return current_iter

    def closeItem(self):
        self.click_at_location_name("close_item")

    def merge_screenshot(self, original: np.array, sells: np.array = None, buys: np.array = None) -> np.ndarray:
        if buys is not None:
            split_point = self.config["buy_box"][3] - self.config["item"][1]
            top = original[:split_point, :]
            bottom = original[split_point:, :]
            original = np.concatenate((top, buys, bottom), axis=0)
        if sells is not None:
            split_point = self.config["sell_box"][3] - self.config["item"][1]
            top = original[:split_point, :]
            bottom = original[split_point:, :]
            original = np.concatenate((top, sells, bottom), axis=0)
        return original

    def improvedScanItem(self) -> np.ndarray:
        initial_screenshot = self.take_screenshot_of_region("item")
        sell_screenshot, buy_screenshot = None, None
        if ImageGrab.grab().getpixel(self.config["sell_wheel"]) == (143, 143, 143):
            while ImageGrab.grab().getpixel(self.config["sell_wheel"]) == (143, 143, 143):
                self.click_at_location_name("sell_wheel")
                pydirectinput.dragRel(None, 180, 0.5, button="left")
            sell_screenshot = self.take_screenshot_of_region("sell_box")
        if ImageGrab.grab().getpixel(self.config["buy_wheel"]) == (143, 143, 143):
            while ImageGrab.grab().getpixel(self.config["buy_wheel"]) == (143, 143, 143):
                self.click_at_location_name("buy_wheel")
                pydirectinput.dragRel(None, 180, 0.5, button="left")
            buy_screenshot = self.take_screenshot_of_region("buy_box")
        final_screenshot = self.merge_screenshot(
            initial_screenshot, 
            sell_screenshot, 
            buy_screenshot
        )
        return final_screenshot, sell_screenshot is not None, buy_screenshot is not None

    def jiggle(self):
        pydirectinput.move(0, 1)
        pydirectinput.move(0, -1)

    def click_at(self, x, y):
        pydirectinput.moveTo(x, y)
        self.jiggle()
        pydirectinput.click()
        self.jiggle()
        pydirectinput.click()

    def click_once_at(self, x, y):
        pydirectinput.moveTo(x, y)
        self.jiggle()
        pydirectinput.click()

    def click_at_location_name(self, name):
        self.click_once_at(*self.config[name])

    def click_at_location_name_with_offet(self, name, offset):
        x_y = self.config[name]
        x = x_y[0]
        y = x_y[1] + offset
        self.click_once_at(x, y)

    def take_screenshot_of_region(self, region):
        region_bounds = self.config[region]
        usable_bounds = self.raw_region_to_usable_region(region_bounds)
        return self.take_photo_with_predefined_coords(usable_bounds)

    def take_photo_with_predefined_coords(self, coords):
        img = pyautogui.screenshot(region=coords)
        np_array = np.array(img)
        return np_array

    def raw_region_to_usable_region(self, old):
        diff_x = old[2] - old[0]
        diff_y = old[3] - old[1]
        return([old[0], old[1], diff_x, diff_y])

    def waitForItemLoad(self):
        start = time.perf_counter()
        grab = ImageGrab.grab()
        clicked = False
        clicked2= False
        while grab.getpixel(self.config["item_background"]) != (20, 20, 20):
            self.click_at_location_name("open_item")
            # if time.perf_counter() - start > 1 and not clicked:
            #     self.click_at_location_name("open_item") # This works really well for catching the item
            #     clicked = True
            # if time.perf_counter() - start > 2 and not clicked2:
            #     self.click_at_location_name("open_item") # This works really well for catching the item
            #     clicked2 = True
            if time.perf_counter() - start > 5:
                return False
            grab = ImageGrab.grab()
        return True