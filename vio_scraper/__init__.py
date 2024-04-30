import os
from .extraction import ImageProcessing
if os.name == "nt":
    from .scrape import ItemScraper, ItemNotFound
    from .login import ProcessManager
    from .ram import RAM