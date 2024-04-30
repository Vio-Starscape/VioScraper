import toml
import os
import cv2
import regex
import pytesseract
from PIL import Image
import numpy as np

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class ImageProcessing:
    def __init__(self):
        self.config = toml.loads("""
item_name = [ 2, 4, 200, 17,]

[buy]
price = [ 8, 350, 108, 550,]
quantity = [ 118, 350, 208, 550,]
vendor_id = [ 225, 350, 310, 550,]

[sell]
price = [ 8, 120, 108, 320,]
quantity = [ 118, 120, 208, 320,]
vendor_id = [ 225, 120, 310, 320,]
""")
        self.extra_buy = 195
        self.extra_sell = 197

    def extract_data_from_image(self, img: Image, buys: bool = False, sells: bool = False):
        data = {
            "name": self.get_title(img),
            "buy": self.get_buy(img, buys, sells),
            "sell": self.get_sell(img, sells),
        }
        return data
        

    def extract_region(self, image_object: np.ndarray,
                   region: tuple[int, int, int, int]) -> np.ndarray:
        return image_object[region[1]: region[3], region[0]: region[2]]
    
    def process_image(self, img: Image, region: tuple[int, int, int, int]):
        img = np.array(img)
        img = self.extract_region(img, region)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        img = cv2.bitwise_not(img)
        img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return img
    
    def text_striping(self, text: str):
        text = text.strip("\n ")
        text = regex.sub(r"\n[\s]+", "\n", text)
        text = regex.sub(r"\n?Station|[\s]+$", "", text)
        text = text.replace("VYexnium", "Vexnium")
        return text
    
    def get_item_name(self, img: Image):
        name = pytesseract.image_to_string(img, config="--psm 7")
        name = self.text_striping(name)
        name = regex.sub(r"[^a-zA-Z\(\)-\s]", "", name)
        name = regex.sub(r"^-|-$", "", name)
        return name.strip()
    
    def get_title(self, img: Image.Image):
        title = self.process_image(img, self.config["item_name"])
        kern = np.ones((4, 1), np.uint8)
        title = cv2.GaussianBlur(title, (3, 1), 2)
        title = cv2.morphologyEx(title, cv2.MORPH_OPEN, kern)

        text = self.text_striping(pytesseract.image_to_string(title, config="--psm 7"
                                                              " -c tessedit_char_whitelist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ()[]-0123456789 '"))
        text = regex.sub(r"\s(?:I|T|L){1,3}(?=\s|$)", lambda match: match.group(0).replace("T", "I"), text)
        return text.strip().replace("@", "0").replace("[", "I").replace("]", "l")
    
    def there_is_anerror(self, data):
        seen = set()
        result = []
        for item in data:
            two = (item[0], item[1])
            if two not in seen:
                seen.add(two)
                result.append(item)
        return result

    def get_buy(self, img: Image.Image, buys: bool = False, sells: bool = False):

        data = {
            "price": [],
            "quantity": [],
            "vendor_id": [],
        }
        def fix_box(bound):
            if buys:
                bound[3] += self.extra_buy
            if sells:
                bound[1] += self.extra_sell
                bound[3] += self.extra_sell
            return bound

        ## Prices
        section = self.process_image(img, fix_box(self.config["buy"]["price"]))
        text = self.text_striping(
            pytesseract.image_to_string(
                section,
                config="--psm 6 -c tessedit_char_whitelist=0@123456789,."
            )
        )

        text = text.replace("@", "0")
        
        text = regex.sub(r"[, ]", "", text)
        for line in text.splitlines():
            data["price"].append(float(line))

        ## Quantities
        section = self.process_image(img, fix_box(self.config["buy"]["quantity"]))
        text = self.text_striping(
            pytesseract.image_to_string(
                section,
                config="--psm 6 -c tessedit_char_whitelist=0@123456789,."
            )
        )
        text = text.replace("@", "0")
        text = regex.sub(r"[\., ]", "", text)
        for line in text.splitlines():
            data["quantity"].append(int(line))

        ## Vendor IDs
        section = self.process_image(img, fix_box(self.config["buy"]["vendor_id"]))
        text = self.text_striping(
            pytesseract.image_to_string(
                section,
                config="--psm 6 -c tessedit_char_whitelist=0123456789,."
            )
        )
        text = regex.sub(r"[\., ]", "", text)
        for line in text.splitlines():
            the_id = int(line)
            if the_id == 40034838611:
                the_id = 4003488611
            data["vendor_id"].append(the_id)

        final = sorted(self.there_is_anerror([
            (price, quantity, vendor_id)
            for price, quantity, vendor_id in zip(data["price"], data["quantity"], data["vendor_id"])
        ]), key=lambda x: x[0], reverse=True)


        return final
    
    def get_sell(self, img: Image.Image, sells: bool = False):
        
        data = {
            "price": [],
            "quantity": [],
            "vendor_id": [],
        }
        def fix_box(bound):
            if sells:
                bound[3] += self.extra_sell
            return bound

        ## Prices
        section = self.process_image(img, fix_box(self.config["sell"]["price"]))
        text = self.text_striping(
            pytesseract.image_to_string(
                section,
                config="--psm 6 -c tessedit_char_whitelist=@0123456789,."
            )
        )

        text = text.replace("@", "0")
        
        text = regex.sub(r"[, ]", "", text)
        for line in text.splitlines():
            data["price"].append(float(line))

        ## Quantities
        section = self.process_image(img, fix_box(self.config["sell"]["quantity"]))
        text = self.text_striping(
            pytesseract.image_to_string(
                section,
                config="--psm 6 -c tessedit_char_whitelist=0@123456789,."
            )
        )
        text = text.replace("@", "0")
        text = regex.sub(r"[\., ]", "", text)
        for line in text.splitlines():
            data["quantity"].append(int(line))

        ## Vendor IDs
        section = self.process_image(img, fix_box(self.config["sell"]["vendor_id"]))
        text = self.text_striping(
            pytesseract.image_to_string(
                section,
                config="--psm 6 -c tessedit_char_whitelist=0123456789,."
            )
        )
        text = regex.sub(r"[\., ]", "", text)
        for line in text.splitlines():
            the_id = int(line)
            if the_id == 40034838611:
                the_id = 4003488611
            data["vendor_id"].append(the_id)

        final = sorted(self.there_is_anerror([
            (price, quantity, vendor_id)
            for price, quantity, vendor_id in zip(data["price"], data["quantity"], data["vendor_id"])
        ]), key=lambda x: x[0])

        return final
