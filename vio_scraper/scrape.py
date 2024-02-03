import logging
import pydirectinput
import pyautogui
import numpy as np
import time
import keyboard
import multiprocessing
from queue import Queue
from threading import Thread
from concurrent.futures import ProcessPoolExecutor
from PIL import ImageGrab, Image
from .extraction import ImageProcessing
from datetime import datetime, timezone

logger = logging.getLogger("LucaScraper")

class ItemNotFound(Exception):
    pass

def unknown_worker(data):
    img = ImageProcessing()
    info = img.extract_data_from_image(data["image"], data["extra_buy"], data["extra_sell"])
    return {
        "name": info["name"],
        "data": info
    }

class ItemScraper:

    max_rows = 8
    table_scale = 2 # Upscale for orders
    row_height = 37

    def __init__(self, config: dict, model_path: str = None) -> None:
        self.config = config
        self.model_path = model_path
        self.processor = ImageProcessing()

    def grab_images(self, queue, config):
        count = 0
        while not keyboard.is_pressed("q"):
            pydirectinput.press("enter")
            self.click_at_location_name("open_item")
            self.click_at_location_name("open_item")
            if not self.waitForItemLoad():
                break
            img, extra_sells, extra_buys = self.improvedScanItem()
            Image.fromarray(img).save(f"unknown{count}.png")
            count += 1
            queue.put(
                {
                    "name": "unknown",
                    "extra_sell": extra_sells,
                    "extra_buy": extra_buys,
                    "image" : img
                }
            )
            self.closeItem()
            pydirectinput.press("down")

    def process_images(self, queue, executor, current_iter, cpus=8):
        images = []
        while True:
            data = queue.get()
            if data is None:  # sentinel value to indicate end of processing
                break
            images.append(data)
            if len(images) == cpus:
                results = list(executor.map(unknown_worker, images))
                for result in results:
                    if result["name"].endswith("tag"):
                        continue
                    if result["name"] not in current_iter["items"]:
                        current_iter["items"][result["name"]] = result["data"]
                    else:
                        current_iter["items"][result["name"]]["buy"].extend(result["data"]["buy"])
                        current_iter["items"][result["name"]]["sell"].extend(result["data"]["sell"])
                images = []

    def new_complete_scrape(self, location: str = "c1"):
        current_iter = {
            "location": location,
            "time_scanned": datetime.now(timezone.utc),
            "items": {}
        }
        pydirectinput.press("\\")
        pydirectinput.press("down")
        pydirectinput.press("down")
        pydirectinput.press("down")
        cpus = multiprocessing.cpu_count()
        queue = Queue()
        with ProcessPoolExecutor(max_workers=cpus) as executor:
            grabber = Thread(target=self.grab_images, args=(queue, self.config))
            processor = Thread(target=self.process_images, args=(queue, executor, current_iter, cpus))
            grabber.start()
            processor.start()
            grabber.join()
            queue.put(None)  # signal to processor that grabbing is done
            processor.join()
        self.click_at_location_name("Armor")
        self.click_at_location_name("All")
        pydirectinput.press("\\")
        pydirectinput.press("\\")
        pydirectinput.press("\\")
        pydirectinput.press("\\")
        pydirectinput.press("\\")
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
        count = 0
        while True:
            grab = ImageGrab.grab()
            val = grab.getpixel(self.config["first_sell_row"]) != (35, 35, 35)\
                and grab.getpixel(self.config["first_buy_row"]) != (35, 35, 35)\
                    and grab.getpixel(self.config["item_background"]) != (20, 20, 20)
            if not val:
                count += 1
            if count > 5:
                return True
            if time.perf_counter() - start > 5:
                return False