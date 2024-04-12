import requests
import psutil
import pygetwindow
from PIL import ImageGrab
import pydirectinput
import time
from discord_webhooks import DiscordWebhooks

class RAM:
    def __init__(self, webhook_url: str, password: str, baseuri:str, config: dict):
        self.webhook_url = webhook_url
        self.password = password
        self.config = config
        self.baseuri = baseuri

        self.current_account = None

    def __enter__(self):
        while self.login_sequence():
            pass
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.exit_roblox()

    def jiggle_mouse(self):
        pydirectinput.moveRel(1, 1)
        time.sleep(0.01)
        pydirectinput.moveRel(-1, -1)
    
    def login_sequence(self):

        accounts = self.get_non_yoinked_accounts()
        if len(accounts) == 0:
            return False
        self.current_account = accounts[0]
        self.launch_account()

        print("Using account: ", self.current_account)

        def wait_for(func, *args, func2 = None):
            initial = time.perf_counter()
            while not func(*args):
                if func2:
                    func2()
                if time.perf_counter() - initial > 20:
                    return False
            return True
        wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["starscape_color"]), 
            *self.config["starscape_logo"],
            func2=self.bring_to_front
        )
        print("Found logo")
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

    def exit_roblox(self):
        for proc in psutil.process_iter():
            if proc.name() == "RobloxPlayerBeta.exe":
                proc.kill()

    def get_accounts_json(self):
        r = requests.get(f'{self.baseuri}/GetAccountsJson?Password={self.password}')
        return {
            i["Username"]: i["Description"]
            for i in r.json()
        }

    def get_non_yoinked_accounts(self):
        accounts = self.get_accounts_json()
        return list(map(lambda x: x[0],filter(lambda x: "yoinked" not in x[1], accounts.items())))

    def launch_account(self):
        account = self.current_account
        try:
            r = requests.get(f'{self.baseuri}/LaunchAccount?Account={account}&PlaceId=679715583&Password={self.password}', timeout=1)
        except requests.exceptions.ReadTimeout:
            return
        
    def bring_to_front(self):
        try:
            windows = pygetwindow.getWindowsWithTitle("Roblox")
            for window in windows:  
                if window.title == "Roblox":
                    window.activate()
                    pydirectinput.click()
        except IndexError:
            pass
        
    def mark_account_as_yoinked(self, account: str):
        r = requests.post(
            f'{self.baseuri}/SetDescription?Account={account}&Password={self.password}',
            data="yoinked"
        )
        hook = DiscordWebhooks(webhook_url=self.webhook_url)
        hook.set_content(title="Account Yoinked", description=f"Account {account} has been yoinked")
        hook.add_field(name="List of accounts", value="\n".join([f"{name}: {desc if desc else 'Good'}" for name, desc in self.get_accounts_json().items()]))
        hook.send()

    def unmark_yoinked_account(self, account: str):
        r = requests.post(
            f'{self.baseuri}/SetDescription?Account={account}&Password={self.password}',
            data=""
        )

        return r