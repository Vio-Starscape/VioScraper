import time
import cv2
import logging
import pydirectinput
import pyautogui
import os
import json
import numpy as np
import multiprocessing
from PIL import ImageGrab, Image, ImageDraw
from .extraction import TableExtraction
from datetime import datetime, timezone

logger = logging.getLogger("LucaScraper")

#import data from config1080p.json
dir_path = os.path.dirname(os.path.realpath(__file__))
dir_path = os.path.join(dir_path, "config1080p.json")
with open(dir_path) as f:
    coordinates = json.load(f)

class ItemNotFound(Exception):
    pass

############################
# Config                   #
############################

def worker_init(path: str | None):
    global table
    table = TableExtraction(
        rec_model_dir=path,
    )

def worker(data):
    return table.extract_table(data)

class ItemScraper:

    max_rows = 8
    table_scale = 2 # Upscale for orders
    row_height = 17

    def __init__(self, model_path: str = None) -> None:
        self.model_path = model_path

    def better_scrape(self, items: list, location: str = "c1"):
        current_iter = {
            "location": location,
            "time_scanned": datetime.now(timezone.utc),
            "items": {}
        }
        cpus = multiprocessing.cpu_count()
        with multiprocessing.Pool(min(cpus, len(items)), initializer=worker_init, initargs=(self.model_path,)) as p:
            images = []
            for item in items:
                logger.debug("Scraping item: " + item)
                while True:
                    self.focusItemInList(item)
                    time.sleep(0.5)

                    if self.validate_item_exists():
                        x = 0
                        while not (ImageGrab.grab().getpixel(tuple(coordinates["item_x"])) == (240,240,240)):
                            self.openXItemInList(0)
                            x += 1
                            if x > 10:
                                raise ItemNotFound(f"{item} not found")
                        self.waitForItemLoad()
                        item_scan = self.improvedScanItem()
                        self.closeItem()
                        images.append(
                            {
                                "name": item,
                                "image" : item_scan
                            }
                        )
                        break
                    else:
                        continue
            
            groups = [images[i:i + cpus] for i in range(0, len(images), cpus)]
            for group in groups:
                results = p.map(worker, group)
                for result in results:
                    data = self.scanItem(result["data"])
                    current_iter["items"][result["name"]] = data
            current_iter["end_time_scanned"] = datetime.now(timezone.utc)
        return current_iter

    def openXItemInList(self, x):
        self.click_at_location_name_with_offet("first_row", x * self.row_height)
        self.click_at_location_name("open_item")


    def validate_item_exists(self):
        coords = tuple(coordinates["first_row"])
        return ImageGrab.grab().getpixel(coords) != (30,30,30)

    def focusItemInList(self, name):
        self.click_at_location_name("search")
        time.sleep(1)
        pydirectinput.write(name, interval=0.1)
        pydirectinput.press("enter")
        time.sleep(1)

    def openTopItemInList(self):
        self.click_at_location_name("first_row")
        self.click_at_location_name("open_item")

    def closeItem(self):
        self.click_at_location_name("close_item")

    def merge_screenshot(self, original: np.array, sells: np.array = None, buys: np.array = None) -> np.ndarray:
        if buys is not None:
            split_point = coordinates["buy"][3] - coordinates["item"][1]
            top = original[:split_point, :]
            bottom = original[split_point:, :]
            original = np.concatenate((top, buys, bottom), axis=0)
        if sells is not None:
            split_point = coordinates["sell"][3] - coordinates["item"][1]
            top = original[:split_point, :]
            bottom = original[split_point:, :]
            original = np.concatenate((top, sells, bottom), axis=0)

        height = original.shape[0]
        original_pil = Image.fromarray(original)
        draw = ImageDraw.Draw(original_pil)
        height = original_pil.height
        for x in [76, 210]:
            draw.line([(x, 0), (x, height)], fill=(0, 0, 0), width=5)

        original = np.array(original_pil)

        return original

    def improvedScanItem(self) -> np.ndarray:
        inital_screenshot = self.take_screenshot_of_region("item")
        sell_screenshot, buy_screenshot = None, None
        if self.get_color_at_pixel(coordinates["sell_wheel"]) == (143, 143, 143):
            while self.get_color_at_pixel(coordinates["sell_wheel"]) == (143, 143, 143):
                self.click_at_location_name("sell_wheel")
                pydirectinput.dragRel(None, 180, 0.5, button="left")
            sell_screenshot = self.take_screenshot_of_region("sell")
        if self.get_color_at_pixel(coordinates["buy_wheel"]) == (143, 143, 143):
            while self.get_color_at_pixel(coordinates["buy_wheel"]) == (143, 143, 143):
                self.click_at_location_name("buy_wheel")
                pydirectinput.dragRel(None, 180, 0.5, button="left")
            buy_screenshot = self.take_screenshot_of_region("buy")
        final_screenshot = self.merge_screenshot(
            inital_screenshot, 
            sell_screenshot, 
            buy_screenshot
        )
        return final_screenshot
    
    def extract_listings(self, data: list[tuple[str, str, str]]):
        listings = data[5:]
        sells, buys = [], []
        buy_flag = False
        for listing in listings:
            if listing[2] == "Station":
                continue
            if listing[2].isdigit():
                if buy_flag:
                    buys.append(listing)
                else:
                    sells.append(listing)
            else:
                buy_flag = True
        return sells, buys

    def scanItem(self, data):
        print(data)
        name = data[0][0]
        volume = data[3][2]

        sells, buys = self.extract_listings(data)

        def clean_input(x: str, n: list[tuple[str, str, str]], index: int = 2):
            if x == "":
                if index == 0:
                    max_price = max([float(x[0]) for x in n if x[0] != ""])
                    if max_price < 6:
                        return 4
                    else:
                        return 6
                elif index == 1:
                    return 1
            return x.replace(",", "").replace(" ", "").replace("/", "7").replace("A", "4")
        
        sells = sorted(
            list(set([
                (float(clean_input(x[0], sells, 0)), int(clean_input(x[1], sells, 1)), int(clean_input(x[2], sells))) 
                for x in sells if x[2] != "Station"
            ])), 
            key=lambda x: x[0]
        )

        buys = sorted(
            list(set([
                (float(clean_input(x[0], buys, 0)), int(clean_input(x[1], buys, 1)), int(clean_input(x[2], buys))) 
                for x in buys if x[2] != "Station"
            ])), 
            key=lambda x: x[0],
            reverse=True
        )

        payload = {
            "name": name,
            "volume": volume, 
            "buy": buys,
            "sell":  sells,
        }
        logger.debug(payload)
        return payload

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
        self.click_once_at(*coordinates[name])

    def click_at_location_name_with_offet(self, name, offset):
        x_y = coordinates[name]
        x = x_y[0]
        y = x_y[1] + offset
        self.click_once_at(x, y)

    def take_screenshot_of_region(self, region):
        region_bounds = coordinates[region]
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
        counter = 0
        count = 0
        time.sleep(0.001)
        while counter < 30:
            if count > 5: 
                return True
            if type == "sell":
                if self.validate_color_at_coords(coordinates["first_sell_row"], 32): count += 1
            else:
                if self.validate_color_at_coords(coordinates["first_buy_row"], 32): count += 1
            counter += 1
            time.sleep(0.1)
        return False

    def validate_color_at_coords(self, coordinates, brightness):
        pixel = self.get_color_at_pixel(coordinates)
        if pixel[0] > brightness or pixel[1] > brightness or pixel[2] > brightness:
            return True
        else:
            return False

    def get_color_at_pixel(self, coordinates):
        try:
            pixel = pyautogui.pixel(coordinates[0], coordinates[1])
        except: 
            pixel = pyautogui.pixel(coordinates[0], coordinates[1])
        return pixel

    def validate_consistent_color_at_coords(self, coordinates, brightness, min = 8):
        counter = 0
        hits = 0
        last_pixel = self.get_color_at_pixel(coordinates)
        while counter < 30:
            logger.debug(last_pixel)
            current_pixel = self.get_color_at_pixel(coordinates)
            if last_pixel != current_pixel: 
                hits = 0
                last_pixel = current_pixel
            if hits > min:
                logger.debug("exists")
                return True
            if(self.validate_color_at_coords(coordinates, brightness)): hits += 1
            elif hits > 0: hits += -1
            counter += 1
        logger.debug("not open")
        return False
    