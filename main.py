import os
import logging
import time
import datetime
import toml
import requests
import keyboard
import json
import threading
import pytesseract
import winreg
import psutil
import customtkinter as ctk
import tkinter.scrolledtext as tkst
import tkinter as tk
from dotenv import load_dotenv
from vio_scraper import ItemScraper, ItemNotFound, RAM

load_dotenv(override=True)

stop_threads = False

logger = logging.getLogger("LucaScraper")

def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def add_scan_to_database(items: dict, url: str, api_key: str):
    try:
        logger.info("Adding to database")
        if len(items["items"]) < 100:
            return
        res = requests.post(
            url,
            headers={"x-api-key": api_key},
            json=json.loads(json.dumps(items, default=datetime_handler)),
            timeout=50
        )
        if res.status_code != 200:
            logger.error(f"Failed to add scan to database!")
            logger.error("Check if the server is running and the API key is correct!")
    except Exception as e:
        logger.error(e)

def scrape_func(
        config: dict,
        discord_webhook_uri: str,
        ram_password: str,
        ram_url: str,
        scraper_url: str,
        api_key: str,
        api_url: str,
        buy_tab: bool,
        ):
    global stop_threads
    memory = {}
    broken = False
    while not broken and not stop_threads:
        try:
            with RAM(
                    discord_webhook_uri,
                    ram_password,
                    ram_url,
                    scraper_url,
                    api_key,
                    config) as process:
                starscraper = ItemScraper(config, buy_tab=buy_tab)
                while not broken and not stop_threads:
                    try:
                        start = time.perf_counter()
                        resp = starscraper.new_complete_scrape()
                        add_scan_to_database(resp, api_url, api_key)
                        end = time.perf_counter()
                        memory[process.current_account] = 0
                        if end-start < 10:
                            raise Exception("Scrape took less than 10 seconds! Restarting...")
                        print("Time taken: ", end - start)
                    except ItemNotFound as e:
                        logger.warning("Item not found!, Adding Strike to account.")
                        if process.current_account not in memory:
                            memory[process.current_account] = 1
                        else:
                            memory[process.current_account] += 1
                        if memory[process.current_account] >= 4:
                            process.mark_account_as_yoinked(process.current_account)
                        break
        except KeyboardInterrupt:
            stop_threads = True
            logger.info("Scraping Stopped!")
        except Exception as e:
            logger.error(e)

class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

        # Define tags for each color
        self.text.tag_config("INFO", foreground="green")
        self.text.tag_config("DEBUG", foreground="grey")
        self.text.tag_config("WARNING", foreground="orange")
        self.text.tag_config("ERROR", foreground="red")
        self.text.tag_config("CRITICAL", foreground="red", underline=1)

    def emit(self, record):
        msg = self.format(record)

        if record.levelno == logging.INFO:
            color = "INFO"
        elif record.levelno == logging.DEBUG:
            color = "DEBUG"
        elif record.levelno == logging.WARNING:
            color = "WARNING"
        elif record.levelno == logging.ERROR:
            color = "ERROR"
        elif record.levelno == logging.CRITICAL:
            color = "CRITICAL"
        else:
            color = "INFO"

        def append():
            self.text.configure(state='normal')
            self.text.insert(ctk.END, msg + '\n', color)
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(ctk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)

class myGUI(ctk.CTk):

    # This class defines the graphical user interface 
    scrape_thread = None

    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        ctk.set_appearance_mode("dark")
        self.configure(background='black')
        self.logger = logging.getLogger()

        self.build_gui()

        check_thread = threading.Thread(target=self.__run_checks)
        check_thread.daemon = True
        check_thread.start()

    def build_gui(self):                    
        # Build GUI
        self.title('Vio Scraper')
        self.option_add('*tearOff', 'FALSE')

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(column=0, row=0, sticky='nsew')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_tab = self.tabs.add("Main")
        self.settings_tab = self.tabs.add("Settings")
        
        self.__setup_logging()

        self.refresh_checks_button = ctk.CTkButton(self.main_tab, text="Recheck ↺", command=self.__run_checks)
        self.refresh_checks_button.place(relx=0.5, rely=0.1, anchor='center')

        self.start_button = ctk.CTkButton(self.main_tab, text="Start Scraping", command=self.__start_scraping, state='disabled')
        self.start_button.place(relx=0.5, rely=0.25, anchor='center')

        self.__setup_settings()

        # Get all config files
        try:
            config_files = os.listdir("configs/screens")

            self.config_label = ctk.CTkLabel(self.settings_tab, text="Select Config File:")
            self.config_label.place(relx=0.5, rely=0.05, anchor='center')

            self.selected_config = ctk.StringVar(value=config_files[0])
            self.config_dropdown = ctk.CTkOptionMenu(
                self.settings_tab,
                values=config_files,
                variable=self.selected_config,
                command=lambda x: self.logger.info(f"Selected config: {self.selected_config.get()}")
            )
            self.config_dropdown.place(relx=0.5, rely=0.1, anchor='center')
        except FileNotFoundError:
            self.logger.error("No config files found in the configs directory. Please add the default files or your own files. and restart the program.")
            return

    def __setup_settings(self):

        with open("configs/settings.toml", "r") as f:
            settings = toml.load(f)

        self.ram_url_label = ctk.CTkLabel(self.settings_tab, text="RAM URL:")
        self.ram_url_label.place(relx=0.25, rely=0.05, anchor='center')
        self.RAM_URL = ctk.CTkEntry(self.settings_tab)
        self.RAM_URL.insert(0, settings.get('RAM_URL', ''))
        self.RAM_URL.place(relx=0.25, rely=0.1, relwidth=0.25, anchor='center')

        self.ram_password_label = ctk.CTkLabel(self.settings_tab, text="RAM Password:")
        self.ram_password_label.place(relx=0.25, rely=0.20, anchor='center')
        self.RAM_PASSWORD = ctk.CTkEntry(self.settings_tab)
        self.RAM_PASSWORD.insert(0, settings.get('RAM_PASSWORD', ''))
        self.RAM_PASSWORD.place(relx=0.25, rely=0.25, relwidth=0.25, anchor='center')

        self.api_url_label = ctk.CTkLabel(self.settings_tab, text="API URL:")
        self.api_url_label.place(relx=0.75, rely=0.05, anchor='center')
        self.API_URL = ctk.CTkEntry(self.settings_tab)
        self.API_URL.insert(0, settings.get('API_URL', ''))
        self.API_URL.place(relx=0.75, rely=0.1, relwidth=0.25, anchor='center')

        self.scraper_url_label = ctk.CTkLabel(self.settings_tab, text="Scraper URL:")
        self.scraper_url_label.place(relx=0.75, rely=0.20, anchor='center')
        self.SCRAPER_URL = ctk.CTkEntry(self.settings_tab)
        self.SCRAPER_URL.insert(0, settings.get('SCRAPER_URL', ''))
        self.SCRAPER_URL.place(relx=0.75, rely=0.25, relwidth=0.25, anchor='center')


        self.vio_api_key_label = ctk.CTkLabel(self.settings_tab, text="VIO API Key:")
        self.vio_api_key_label.place(relx=0.75, rely=0.35, anchor='center')
        self.VIO_API_KEY = ctk.CTkEntry(self.settings_tab)
        self.VIO_API_KEY.insert(0, settings.get('VIO_API_KEY', ''))
        self.VIO_API_KEY.place(relx=0.75, rely=0.4, relwidth=0.25, anchor='center')
            
        self.discord_webhook_label = ctk.CTkLabel(self.settings_tab, text="Discord Webhook:")
        self.discord_webhook_label.place(relx=0.25, rely=0.35, anchor='center')
        self.DISCORD_WEBHOOK = ctk.CTkEntry(self.settings_tab)
        self.DISCORD_WEBHOOK.insert(0, settings.get('DISCORD_WEBHOOK_URI', ''))
        self.DISCORD_WEBHOOK.place(relx=0.25, rely=0.4, relwidth=0.25, anchor='center')

        self.BUY_TAB = ctk.CTkCheckBox(self.settings_tab, text="Buy Tab")
        if bool(settings.get('BUY_TAB', False)):
            self.BUY_TAB.select()
        else:
            self.BUY_TAB.deselect()
        self.BUY_TAB.place(relx=0.5, rely=0.55, anchor='center')
        

    def __setup_logging(self):
        # This function will setup the logging configuration

        # Add text widget to display logging info

        st = ctk.CTkTextbox(self.main_tab, state='disabled')
        st.configure(font=('TkFixedFont', 12))
        st.place(relx=0, rely=0.3, relwidth=1, relheight=0.7)

        # Create textLogger
        text_handler = TextHandler(st)

        # If applicable, remove all handlers from the root logger
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Set the logging level and format
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s::%(levelname)s: %(message)s', "%Y-%m-%d %H:%M:%S")
        text_handler.setFormatter(formatter)

        # Add the handler to logger
        self.logger.addHandler(text_handler)
        
        
    def __run_checks(self):
        # This function will run checks to ensure that the user has the correct dependencies installed
        self.logger.info("Running checks...")

        self.logger.info("Checking if OS is Windows...")
        if os.name != "nt": # Shouldn't need since it will be an EXE and probably won't work on other OS
            self.logger.error("This program only supports Windows.")
            return
        
        # Check if Tesseract is installed
        self.logger.info("Checking if Tesseract is installed...")
        
        if not os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
            self.logger.error("Tesseract is not installed.")
            self.logger.error("Please install Tesseract here (https://github.com/UB-Mannheim/tesseract/wiki) before continuing.")
            self.logger.error("Currently the program is looking for Tesseract in C:\\Program Files\\Tesseract-OCR\\tesseract.exe.")
            return

        # Checking if RobloxAccountManager is running
        self.logger.info("Checking if RobloxAccountManager is running...")
        if "Roblox Account Manager.exe" not in [proc.name() for proc in psutil.process_iter()]:
            self.logger.error("RobloxAccountManager is not running.")
            self.logger.error("Please install and run Roblox Account Manager before continuing! Make sure to have some accounts loaded.")
            return

        self.logger.info("Checks completed.")
        self.after(0, self.__enable_start_button)

    def __enable_start_button(self):
        self.start_button.configure(state='normal')

    def __check_config_filled(self):
        # This function will check if the user has selected a config file

        if self.RAM_URL.get() == "":
            self.logger.warning("RAM URL is not filled out.")
            return False
        
        if self.RAM_PASSWORD.get() == "":
            self.logger.warning("RAM Password is not filled out.")
            return False
        
        if self.API_URL.get() == "":
            self.logger.warning("API URL is not filled out.")
            return False
        
        if self.SCRAPER_URL.get() == "":
            self.logger.warning("Scraper URL is not filled out.")
            return False
        
        if self.VIO_API_KEY.get() == "":
            self.logger.warning("VIO API Key is not filled out.")
            return False

        return True

    def __start_scraping(self):
        # This function will start the scraping process and will be blocking until exited
        if not self.__check_config_filled():
            self.logger.error("Data not filled out correctly. Please fill out the data before starting.")
            return
        else:
            with open("configs/settings.toml", "w") as f:
                toml.dump(
                    {
                        "DISCORD_WEBHOOK_URI": self.DISCORD_WEBHOOK.get(), # This is the webhook for the discord server
                        "RAM_URL": self.RAM_URL.get(),
                        "RAM_PASSWORD": self.RAM_PASSWORD.get(),
                        "API_URL": self.API_URL.get(),
                        "SCRAPER_URL": self.SCRAPER_URL.get(),
                        "VIO_API_KEY": self.VIO_API_KEY.get(),
                        "BUY_TAB": self.BUY_TAB.get()
                    },
                    f
                )


        global stop_threads
        stop_threads = False

        if self.scrape_thread and self.scrape_thread.is_alive():
            self.logger.info("Scraping already in progress. Please wait for it to finish.")
            return

        with open(f"configs/screens/{self.selected_config.get()}", "r") as f:
            config = toml.load(f)

        self.scrape_thread = threading.Thread(
            target=scrape_func,
            args=(
                config,
                self.DISCORD_WEBHOOK.get(),
                self.RAM_PASSWORD.get(),
                self.RAM_URL.get(),
                self.SCRAPER_URL.get(),
                self.VIO_API_KEY.get(),
                self.API_URL.get(),
                bool(self.BUY_TAB.get())
                )
            )
        self.scrape_thread.daemon = True
        self.scrape_thread.start()

if __name__ == "__main__":
    app = myGUI()
    app.resizable(False, False)
    app.geometry('960x540')
    app.mainloop()