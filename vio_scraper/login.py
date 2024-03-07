from PIL import ImageGrab
import os
import time
import subprocess
import pydirectinput

class ProcessManager:

    def __init__(self, path: str, config: dict[str, tuple[int, int]]) -> None:
        self.path = path
        self.subprocess = None
        self.config = config

    def __enter__(self):
        self.subprocess = subprocess.Popen([self.find_roblox()])
        while self.login_sequence():
            pass
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.subprocess.kill()
        self.subprocess = None

    def find_roblox(self):
        for folder in os.listdir(self.path):
            if not os.path.isdir(os.path.join(self.path, folder)):
                continue
            for file in os.listdir(os.path.join(self.path, folder)):
                if "RobloxPlayerBeta.exe" in file:
                    return os.path.join(self.path, folder, file)
        raise FileNotFoundError("Could not find RobloxPlayerBeta.exe")

    def jiggle_mouse(self):
        pydirectinput.moveRel(1, 1)
        time.sleep(0.01)
        pydirectinput.moveRel(-1, -1)

    def login_sequence(self):

        def wait_for(func, *args):
            initial = time.perf_counter()
            while not func(*args):
                if time.perf_counter() - initial > 20:
                    return False
            return True
        pydirectinput.moveTo(*self.config["rob_search"])
        if not wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["search_color"]), 
            *self.config["rob_search"]
        ):
            return True
        self.jiggle_mouse()
        pydirectinput.doubleClick()
        time.sleep(0.1)
        pydirectinput.write("Starscape")
        time.sleep(0.1)
        pydirectinput.press("enter")
        if not wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["search_color"]), 
            *self.config["rob_search"]
        ):
            return True
        pydirectinput.moveTo(*self.config["play_button"])
        self.jiggle_mouse()
        time.sleep(2)
        pydirectinput.click()
        wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["starscape_color"]), 
            *self.config["starscape_logo"]
        )
        pydirectinput.moveTo(*self.config["starscape_button"])
        self.jiggle_mouse()
        time.sleep(1)
        pydirectinput.click()
        wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["starscape_health_color"]), 
            *self.config["starscape_health"]
        )
        time.sleep(2)
        pydirectinput.press("f")
        time.sleep(5)
        


if __name__ == "__main__":
    # while True:
    #     print(pydirectinput.position(),ImageGrab.grab().getpixel(pydirectinput.position()))
    config = {
        "search": [839, 50],
        "search_color": [70, 72, 74],
        "play_button": [305, 704],
        "play_button_color": [0, 159, 100],
        "starscape_button": [950, 556],
        "starscape_logo": [964, 451],
        "starscape_color": [240, 216, 95],
        "starscape_health": [917, 986],
        "starscape_health_color": [20, 180, 20],
    }
    path = r"C:\Users\ericm\AppData\Local\Roblox\Versions"

    with ProcessManager(path, config) as process:
        process.login_sequence()
        time.sleep(60)
        pass