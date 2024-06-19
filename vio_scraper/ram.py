import requests
import psutil
import socket
import pygetwindow
from PIL import ImageGrab
import pydirectinput
import time
import logging
from discord_webhooks import DiscordWebhooks

class RAM:
    def __init__(self, webhook_url: str, password: str, ramuri:str, uri: str, apikey:str, config: dict):
        self.webhook_url = webhook_url
        self.password = password
        self.config = config
        self.ramuri = ramuri
        self.uri = uri
        self.apikey = apikey

        self.current_account: dict | None = None

        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self.logger.info("Updating accounts...")
        self.update_there()
        while self.login_sequence():
            pass
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.exit_roblox()
        self.update_there()

    def update_here(self):
        r = requests.get(f'{self.uri}/api/scrapers/getall',
                         params={"host": socket.gethostname()},
                         headers={"x-api-key": self.apikey})
        response_data = r.json()

        current_accounts = self.get_accounts_json()

        for account in response_data:
            if current_accounts[account["name"]] == "yoinked" and not account["yoinked"]:
                self.unmark_yoinked_account(account["name"])
            elif current_accounts[account["name"]] != "yoinked" and account["yoinked"]:
                self.mark_account_as_yoinked(account["name"])
        
        self.logger.info("Update Done!")
    
    def update_there(self):
        account_data = []
        for name, description in self.get_accounts_json().items():
            account_data.append({
                "name": name,
                "active": self.current_account is not None and name in self.current_account,
                "yoinked": "yoinked" in description
            })
        r = requests.post(
            f'{self.uri}/api/scrapers/sync',
            params={"host": socket.gethostname()},
            headers={"x-api-key": self.apikey},
            json=account_data
        )

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

        self.logger.info(f"Using account: {self.current_account}")

        def wait_for(func, *args, func2 = None):
            initial = time.perf_counter()
            while not func(*args):
                if func2:
                    func2()
                if time.perf_counter() - initial > 40:
                    return False
            return True
        if not wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["starscape_color"]), 
            *self.config["starscape_logo"],
            func2=self.bring_to_front
        ):
            return False
        pydirectinput.moveTo(*self.config["starscape_button"])
        pydirectinput.click()
        self.jiggle_mouse()
        time.sleep(1)
        pydirectinput.click()
        if not wait_for(
            lambda x, y: ImageGrab.grab().getpixel((x, y)) == tuple(self.config["starscape_health_color"]), 
            *self.config["starscape_health"]
        ):
            return False
        time.sleep(2)
        pydirectinput.press("f")
        time.sleep(5)

        return False

    def exit_roblox(self):
        for proc in psutil.process_iter():
            if proc.name() == "RobloxPlayerBeta.exe":
                proc.kill()

    def get_accounts_json(self):
        r = requests.get(f'{self.ramuri}/GetAccountsJson?Password={self.password}')
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
            r = requests.get(f'{self.ramuri}/LaunchAccount?Account={account}&PlaceId=679715583&Password={self.password}', timeout=1)
        except requests.exceptions.ReadTimeout:
            pass
        r = requests.post(f'{self.uri}/api/scrapers/update/active',
                         params={"host": socket.gethostname()},
                         headers={"x-api-key": self.apikey},
                         json={"name": account, "active": True, "yoinked": False})
        
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
            f'{self.ramuri}/SetDescription?Account={account}&Password={self.password}',
            data="yoinked"
        )
        r = requests.post(f'{self.uri}/api/scrapers/update/yoinked',
                          params={"host": socket.gethostname()},
                         headers={"x-api-key": self.apikey},
                         json={"name": account, "active": False, "yoinked": True})
        hook = DiscordWebhooks(webhook_url=self.webhook_url)
        hook.set_content(title="Account Yoinked", description=f"Account {account} has been yoinked")
        hook.add_field(name="List of accounts", value="\n".join([f"{name}: {desc if desc else 'Good'}" for name, desc in self.get_accounts_json().items()]))
        hook.send()

    def unmark_yoinked_account(self, account: str):
        r = requests.post(
            f'{self.ramuri}/SetDescription?Account={account}&Password={self.password}',
            data="Primed")
        
