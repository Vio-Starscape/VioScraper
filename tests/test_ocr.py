import sys
sys.path.insert(0, sys.path[0].replace('/tests', ''))

import unittest
import os
from PIL import Image
from vio_scraper.extraction import ImageProcessing

class OCRTest(unittest.TestCase):

    ## MISREAD TITLE TESTS
    def test_misread_titles_all(self):
        process = ImageProcessing()

        for image in os.listdir("tests/examples"):
            img = Image.open(f"tests/examples/{image}")
            title = process.get_title(img)
            self.assertEqual(title, image.removesuffix(".png"))


    ## MISREAD AMOUNT TESTS
    def test_misread_amount1(self):
        process = ImageProcessing()

        image1 = "tests/examples/Water.png"
        buys, sells = False, False
        img = Image.open(image1)
        title = process.get_title(img)
        self.assertEqual(title, "Water")

        sell = process.get_sell(img, sells)
        self.assertEqual(
            sell,
            [
                (49.85, 1020, 2041428980),
                (49.90, 237, 141953152),
                (50.00, 2000, 116941459),
                (59.95, 11111, 2450011336),
            ]
        )

        buy = process.get_buy(img, buys, sells)
        self.assertEqual(
            buy,
            [
                (40.00, 4094, 96806163),
                (38.50, 2429, 170019204),
                (36.55, 11005, 2450011336),
                (31.30, 2000, 47926919),
            ]
        )

    def test_misread_amount2(self):
        process = ImageProcessing()

        image2 = "tests/examples/Water ice.png"
        buys, sells = False, False
        img = Image.open(image2)
        title = process.get_title(img)
        self.assertEqual(title, "Water ice")

        sell = process.get_sell(img, sells)
        self.assertEqual(
            sell,
            [
                (100, 296, 84329237),
                (999_999_999, 1, 1739785754)
            ]
        )

        buy = process.get_buy(img, buys, sells)
        self.assertEqual(
            buy,
            [
                (40.00, 2_000, 96806163),
                (38.90, 573, 170019204),
                (35.20, 2_733, 116941459)
            ]
        )


if __name__ == "__main__":
    unittest.main()