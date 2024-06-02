import time
import os
import logging
import threading
import customtkinter as ctk
import tkinter.scrolledtext as tkst

class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(ctk.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(ctk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)

class myGUI(ctk.CTk):

    # This class defines the graphical user interface 

    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger()
        self.build_gui()


        check_thread = threading.Thread(target=self.__run_checks)
        check_thread.start()

    def build_gui(self):                    
        # Build GUI
        self.title('Vio Scraper')
        self.option_add('*tearOff', 'FALSE')

        self.__setup_logging()

        # Add a button that logs a message when clicked
        self.log_button = ctk.CTkButton(self, text="Log Message", command=lambda: self.logger.info("Button clicked"))
        self.log_button.grid(column=0, row=0, sticky='w')

        self.start_button = ctk.CTkButton(self, text="Start Scraping", command=self.__start_scraping, state='disabled')
        self.start_button.grid(column=1, row=0, sticky='new')

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)


    def __setup_logging(self):
        # This function will setup the logging configuration

        # Add text widget to display logging info
        st = tkst.ScrolledText(self, state='disabled')
        st.configure(font='TkFixedFont', background='black', foreground='white')
        st.grid(column=2, row=2, sticky="se")

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
        if os.name != "nt": # Shouldn't need since it will be an EXE
            self.logger.error("This program only supports Windows.")
            return
        
        # Check if Tesseract is installed
        self.logger.info("Checking if Tesseract is installed...")
        time.sleep(1)
        if False:
            self.logger.error("Tesseract is not installed.")
            self.logger.error("Please install Tesseract here (https://github.com/UB-Mannheim/tesseract/wiki) before continuing.")
            return

        # Checking if Roblox is installed
        self.logger.info("Checking if Roblox is installed...")
        time.sleep(1)
        if False:
            self.logger.error("Roblox is not installed.")
            self.logger.error("Please install Roblox before continuing.")
            return

        # Checking if RobloxAccountManager is installed
        self.logger.info("Checking if RobloxAccountManager is installed...")
        time.sleep(1)
        if False:
            self.logger.error("RobloxAccountManager is not installed.")
            self.logger.error("Please install RobloxAccountManager before continuing.")
            return

        self.logger.info("Checks completed.")
        self.after(0, self.__enable_start_button)

    def __enable_start_button(self):
        self.start_button.configure(state='normal')

    def __start_scraping(self):
        # This function will start the scraping process and will be blocking until exited
        pass


app = myGUI()
app.resizable(False, False)
app.geometry('960x540')
app.mainloop()
