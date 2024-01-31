import time
import logging
import pydirectinput
import pyautogui
import numpy as np
import multiprocessing
import re
from PIL import ImageGrab, Image, ImageDraw
from .extraction import ImageProcessing
from datetime import datetime, timezone

logger = logging.getLogger("LucaScraper")

class ItemNotFound(Exception):
    pass

############################
# Config                   #
############################

def worker(data):
    img = ImageProcessing()
    return {
        "name": data["name"],
        "data": img.extract_data_from_image(data["image"], data["extra_buy"], data["extra_sell"])
    }

class ItemScraper:

    max_rows = 8
    table_scale = 2 # Upscale for orders
    row_height = 37

    def __init__(self, config: dict, model_path: str = None) -> None:
        self.config = config
        self.model_path = model_path
        self.processor = ImageProcessing()

    def better_scrape(self, items: list, location: str = "c1"):
        current_iter = {
            "location": location,
            "time_scanned": datetime.now(timezone.utc),
            "items": {}
        }
        cpus = multiprocessing.cpu_count()
        with multiprocessing.Pool(min(cpus, len(items))) as p:
            images = []
            for item in items:
                logger.debug("Scraping item: " + item)
                self.focusItemInList(item)
                time.sleep(0.5)

                if self.validate_item_exists():
                    x = 0
                    depth = self.getItemDepth()
                    location = 0
                    if depth > 1:
                        location = self.getSpecificItemDepth(item, depth)
                    while not (ImageGrab.grab().getpixel(tuple(self.config["item_x"])) == (240,240,240)):
                        self.openXItemInList(location)
                        x += 1
                        if x > 10:
                            raise ItemNotFound(f"{item} not found")
                    self.waitForItemLoad()
                    item_scan, extra_sells, extra_buys = self.improvedScanItem()
                    self.closeItem()
                    images.append(
                        {
                            "name": item,
                            "extra_sell": extra_sells,
                            "extra_buy": extra_buys,
                            "image" : item_scan
                        }
                    )
                else:
                    current_iter["items"][item] = {
                        "name": item,
                        "buy": [],
                        "sell": []
                    }
            
            groups = [images[i:i + cpus] for i in range(0, len(images), cpus)]
            for group in groups:
                results = p.map(worker, group)
                for result in results:
                    current_iter["items"][result["name"]] = result["data"]
            current_iter["end_time_scanned"] = datetime.now(timezone.utc)
        return current_iter

    def openXItemInList(self, x):
        self.click_at_location_name_with_offet("first_row", x * self.row_height)
        self.click_at_location_name("open_item")

    def validate_item_exists(self):
        coords = tuple(self.config["first_row"])
        return ImageGrab.grab().getpixel(coords) != (30,30,30)

    def focusItemInList(self, name):
        self.click_at_location_name("first_row")
        self.click_at_location_name("search")
        value = re.sub(r"[-(].*", "", name).strip()
        pydirectinput.write(value, interval=0.1)

    def openTopItemInList(self):
        self.click_at_location_name("first_row")
        self.click_at_location_name("open_item")

    def closeItem(self):
        self.click_at_location_name("close_item")

    def getItemDepth(self):
        for i, (x, y) in enumerate(self.config["item_list_location"], start=1):
            if ImageGrab.grab().getpixel((x, y)) == (30,30,30):
                return i-1
        return len(self.config["item_list_location"])
    
    def getSpecificItemDepth(self, item: str, current_depth: int):
        img = Image.fromarray(self.take_screenshot_of_region("item_list"))
        for j in range(current_depth):
            chosen_item = img.crop([n+(j*37) if i%2 == 1 else n for i, n in enumerate(self.config["item_list_name"])])
            name = self.processor.get_item_name(chosen_item)
            if name.lower() == item.lower():
                return j

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
        if self.get_color_at_pixel(self.config["sell_wheel"]) == (143, 143, 143):
            while self.get_color_at_pixel(self.config["sell_wheel"]) == (143, 143, 143):
                self.click_at_location_name("sell_wheel")
                pydirectinput.dragRel(None, 180, 0.5, button="left")
            sell_screenshot = self.take_screenshot_of_region("sell_box")
        if self.get_color_at_pixel(self.config["buy_wheel"]) == (143, 143, 143):
            while self.get_color_at_pixel(self.config["buy_wheel"]) == (143, 143, 143):
                self.click_at_location_name("buy_wheel")
                pydirectinput.dragRel(None, 180, 0.5, button="left")
            buy_screenshot = self.take_screenshot_of_region("buy_box")
        final_screenshot = self.merge_screenshot(
            initial_screenshot, 
            sell_screenshot, 
            buy_screenshot
        )
        return final_screenshot, sell_screenshot is not None, buy_screenshot is not None
    
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
        counter = 0
        count = 0
        time.sleep(0.001)
        while counter < 30:
            if count > 5: 
                return True
            if type == "sell":
                if self.validate_color_at_coords(self.config["first_sell_row"], 32): count += 1
            else:
                if self.validate_color_at_coords(self.config["first_buy_row"], 32): count += 1
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
    