import time
import logging
import pydirectinput
import pyautogui
import tablecv
import os
import json
import numpy as np
from datetime import datetime

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
max_rows = 8
table_scale = 2 # Upscale for orders
row_height = 17

def scrape(items: list, location: str = "c1"):
    current_iter = {
        "location": location,
        "time_scanned": datetime.now().timestamp(),
        "items": {}
    }
    for item in items:
        logger.debug("Scraping item: " + item)
        focusItemInList(item)
        if validate_item_exists(0):
            current_iter["items"][item] = scanList()
        else:
            raise ItemNotFound(f"{item} not found")
    return current_iter

def scrape_single(item: str):
    focusItemInList(item)
    if validate_item_exists(0):
        return scanList()
    else:
        raise ItemNotFound(f"{item} not found")
        
def scanList():
    offset = 0
    row_count = 0
    if validate_item_exists(0):
        openXItemInList(0)
        waitForItemLoad("sell")
        payload = scanItem()
        closeItem()
        if payload != {}:
            return payload
        row_count += 1
        offset += row_height
    else:
        raise ItemNotFound("Item not found")

def openXItemInList(x):
    click_at_location_name_with_offet("first_row", x * row_height)
    click_at_location_name("open_item")


def validate_item_exists(offset):
    coords = coordinates["first_row"]
    xy = [int(coords[0]), int(coords[1])]
    xy[1] += offset
    return validate_consistent_color_at_coords(xy, 40)

def focusItemInList(name):
    click_at_location_name("search")
    pydirectinput.click()
    time.sleep(0.5)
    pydirectinput.write(name)

def openTopItemInList():
    click_at_location_name("first_row")
    click_at_location_name("open_item")

def closeItem():
    click_at_location_name("close_item")

def scanItem():
    data = list(
        tablecv.extract_table(
            take_screenshot_of_region("item")
        ).itertuples(index=False, name=None)
    )
    name = data[0][0]
    volume = data[3][2]

    sells, buys = extract_listings(data)

    clean_input = lambda x: x.replace(",", "").replace(" ", "").replace("/", "7")

    if get_color_at_pixel(coordinates["sell_wheel"]) == (143, 143, 143):
        print("extra sells")
        sells = extract_extra_listings(sells, "sell")
    if get_color_at_pixel(coordinates["buy_wheel"]) == (143, 143, 143):
        print("extra buys")
        buys = extract_extra_listings(buys, "buy")

    print("Before sort")
    print(sells)
    print(buys)

    sells = sorted(
        [
            (float(clean_input(x[0])) if x[0] != "" else 6, int(clean_input(x[1])), int(clean_input(x[2]))) 
            for x in sells if x[2] != "Station"
        ], 
        key=lambda x: x[0]
    )

    buys = sorted(
        [
            (float(clean_input(x[0])) if x[0] != "" else 6, int(clean_input(x[1])), int(clean_input(x[2]))) 
            for x in buys if x[2] != "Station"
        ], 
        key=lambda x: x[0],
        reverse=True
    )
    

    if sells == [] and buys == []:
        logger.debug("An order could not be processed")
        return {}
    payload = {
        "name": name,
        "volume": volume, 
        "buy": buys,
        "sell":  sells,
    }
    logger.debug(payload)
    return payload

def emergency_rescan(reigon: str):
    if reigon == "buy":
        return list(
                tablecv.extract_table(
                    take_screenshot_of_region("sell")
                ).itertuples(index=False, name=None)
        )
    else:
        return list(
                tablecv.extract_table(
                    take_screenshot_of_region("buy")
                ).itertuples(index=False, name=None)
        )

def extract_extra_listings(data: list[tuple[str, str, str]], table: str):
    if table == "buy":
        while get_color_at_pixel(coordinates["buy_wheel"]) == (143, 143, 143):
            click_at_location_name("buy_wheel")
            pydirectinput.dragRel(None, 180, 0.5, button="left")
        added_data = list(
            tablecv.extract_table(
                take_screenshot_of_region("sell")
            ).itertuples(index=False, name=None)
        )
        return list(set(data + added_data))
    else:
        while get_color_at_pixel(coordinates["sell_wheel"]) == (143, 143, 143):
            click_at_location_name("sell_wheel")
            pydirectinput.dragRel(None, 180, 0.5, button="left")
        added_data = list(
            tablecv.extract_table(
                take_screenshot_of_region("buy")
            ).itertuples(index=False, name=None)
        )
        return list(set(data + added_data))

def extract_listings(data: list[tuple[str, str, str]]):
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

def jiggle():
    pydirectinput.move(0, 1)
    pydirectinput.move(0, -1)

def click_at(x, y):
    pydirectinput.moveTo(x, y)
    jiggle()
    pydirectinput.click()
    jiggle()
    pydirectinput.click()

def click_once_at(x, y):
    pydirectinput.moveTo(x, y)
    jiggle()
    pydirectinput.click()

def click_at_location_name(name):
    x_y = coordinates[name]
    x = x_y[0]
    y = x_y[1]
    click_once_at(x, y)

def click_at_location_name_with_offet(name, offset):
    x_y = coordinates[name]
    x = x_y[0]
    y = x_y[1] + offset
    click_once_at(x, y)

def take_screenshot_of_region(region):
    region_bounds = coordinates[region]
    usable_bounds = raw_region_to_usable_region(region_bounds)
    return take_photo_with_predefined_coords(usable_bounds)

def take_photo_with_predefined_coords(coords):
    img = pyautogui.screenshot(region=coords)
    np_array = np.array(img)
    return np_array

def raw_region_to_usable_region(old):
    diff_x = old[2] - old[0]
    diff_y = old[3] - old[1]
    return([old[0], old[1], diff_x, diff_y])

def waitForItemLoad(type):
    counter = 0
    count = 0
    time.sleep(0.001)
    while counter < 30:
        if count > 5: 
            return True
        if type == "sell":
            if validate_color_at_coords(coordinates["first_sell_row"], 32): count += 1
        else:
            if validate_color_at_coords(coordinates["first_buy_row"], 32): count += 1
        counter += 1
        time.sleep(0.1)

def validate_color_at_coords(coordinates, brightness):
    pixel = get_color_at_pixel(coordinates)
    if pixel[0] > brightness or pixel[1] > brightness or pixel[2] > brightness:
        return True
    else:
        return False

def get_color_at_pixel(coordinates):
    try:
        pixel = pyautogui.pixel(coordinates[0], coordinates[1])
    except: 
        pixel = pyautogui.pixel(coordinates[0], coordinates[1])
    return pixel

def validate_consistent_color_at_coords(coordinates, brightness, min = 8):
    counter = 0
    hits = 0
    last_pixel = get_color_at_pixel(coordinates)
    while counter < 30:
        logger.debug(last_pixel)
        current_pixel = get_color_at_pixel(coordinates)
        if last_pixel != current_pixel: 
            hits = 0
            last_pixel = current_pixel
        if hits > min:
            logger.debug("exists")
            return True
        if(validate_color_at_coords(coordinates, brightness)): hits += 1
        elif hits > 0: hits += -1
        counter += 1
    logger.debug("not open")
    return False

if __name__ == "__main__":
    print(extract_extra_listings([], "buy"))