import logging

from src import DBScraper

logging.basicConfig(level=logging.INFO)


with DBScraper(headless=True) as db:
    connection = db.get_connection("München", "Göttingen", 3, True)
    connection.to_csv("./db_test2.csv")

