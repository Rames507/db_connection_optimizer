import logging

from src import DBScraper

logging.basicConfig(level=logging.INFO)


with DBScraper(headless=True) as db:
    connection = db.get_connection("Berlin", "Frankfurt", 7, True)
    connection.to_excel("./ber-frank.xlsx")
