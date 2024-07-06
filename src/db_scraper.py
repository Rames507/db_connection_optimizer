import datetime as dt
import locale
import logging
import os.path
import pathlib
from time import sleep

import bs4
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from src.connection import Connection
from src.xpath_soup import xpath_soup

logger = logging.getLogger(__name__)


class DBScraper:
    def __init__(self, *, headless: bool = True, context_manager: bool = True):
        """
        A Scraper to fetch best prices for a connection from https://int.bahn.de/en

        | Designed for use in a context manager.
        e.g.::

            with DBScraper(headless=True) as db:
                pass

        :param headless: Makes the browser instance headless (invisible)
        :param context_manager: pass 'False' to use outside a context_manager.
            This will not automatically close the driver. Call 'close()' instead.
        """
        self.driver = None
        if not context_manager:
            self.driver = self.setup_driver(headless)
        self.headless = headless

    def __enter__(self):
        self.driver = self.setup_driver(self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.driver.close()

    @staticmethod
    def setup_driver(headless: bool):
        logger.info("Initializing webdriver.")
        options = webdriver.FirefoxOptions()
        options.binary_location = str(
            pathlib.Path(r"C:\Program Files\Mozilla Firefox\firefox.exe").resolve()
        )
        if headless:
            options.add_argument("-headless")

        service = webdriver.FirefoxService(
            executable_path=str(
                pathlib.Path(f"{__file__}/../../driver/geckodriver.exe").resolve()
            )
        )

        driver = webdriver.Firefox(options=options, service=service)

        for extension in pathlib.Path(f"{__file__}/../../extensions/").iterdir():
            file_name, file_ext = os.path.splitext(extension)
            if file_ext == ".xpi":
                driver.install_addon(str(extension))

        driver.implicitly_wait(20)
        return driver

    def get_connection(
        self, origin: str, destination: str, days: int, return_trip: bool = True
    ) -> Connection:
        if not self.driver:
            raise DriverError(
                "Driver not initialized."
                "Use in a context manager or pass 'context_manager=False' when initializing DBScraper."
                "Note that use outside of a context manager will not automatically close the driver instance."
            )

        columns = ("date", "00-07", "07-10", "10-13", "13-16", "16-19", "19-24")

        conn: list[tuple[dt.date, list[float]]] = self._get_connection(
            origin, destination, days
        )
        if return_trip:
            # seems like the simplest way to reset the local storage (gets rid of date position)
            self.driver.close()
            self.driver = self.setup_driver(headless=self.headless)
            return_conn: list[tuple[dt.date, list[float]]] = self._get_connection(
                destination, origin, days
            )
            inward_journey = pd.DataFrame(
                [[c[0], *c[1]] for c in return_conn], columns=columns
            )
        else:
            inward_journey = None

        outward_journey = pd.DataFrame([[c[0], *c[1]] for c in conn], columns=columns)

        return Connection(origin, destination, outward_journey, inward_journey)

    def _get_connection(
        self, origin: str, destination: str, days: int
    ) -> list[tuple[dt.date, list[float]]]:
        logger.info(f"Querying connection. ({origin} --> {destination}; days: {days})")

        self.initial_search(origin, destination)
        sleep(1)
        best_prices: list[tuple[dt.date, list[float]]] = []
        for i in range(1, days + 1):
            logger.info(f"Retrieving price data {i}/{days}")

            best_prices.append(self.get_prices(self.driver.page_source))
            next_page_btn = self.driver.find_element(
                By.CSS_SELECTOR, "span.icon-next2:nth-child(2)"
            )
            if i == days:
                # No need to load the next page for the last day.
                break
            next_page_btn.click()
            # this makes sure we wait until the page is fully loaded, the element itself is not relevant
            try:
                _ = self.driver.find_element(
                    By.CSS_SELECTOR, ".tagesbestpreis-intervall--selected"
                )
            except NoSuchElementException:
                # hope the page will load if we wait a bit longer
                sleep(15)
            sleep(0.5)

        return best_prices

    @staticmethod
    def get_prices(page) -> tuple[dt.date, list[float]]:
        soup = bs4.BeautifulSoup(page, features="lxml")

        price_btns = soup.find_all(
            "span", class_="tagesbestpreis-intervall__button-text"
        )
        price_strs = [price_btn.text for price_btn in price_btns]
        prices = [float(price.split("€")[-1]) for price in price_strs]

        date_str = soup.find("div", class_="db-web-date-scroller__date").text
        day, month, year = date_str.split()[1:]
        day = f"{day.strip('.'):0>2}"

        locale.setlocale(locale.LC_ALL, "en_US")
        date = dt.datetime.strptime(f"{day} {month} {year}", r"%d %b %Y").date()
        locale.setlocale(locale.LC_ALL, "")

        return date, prices

    def initial_search(self, origin, destination):
        self.driver.get("https://int.bahn.de/en/")
        origin_input = self.driver.find_element(By.NAME, "quickFinderBasic-von")
        dest_input = self.driver.find_element(By.NAME, "quickFinderBasic-nach")

        origin_input.send_keys(origin)
        dest_input.send_keys(destination)

        time_selector = self.driver.find_element(
            By.CLASS_NAME, "quick-finder-option-area__heading"
        )
        time_selector.click()
        sleep(0.5)

        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(
            self.driver.page_source, features="lxml"
        )

        current_day = soup.find(
            "div",
            class_="db-web-date-picker-calendar-day db-web-date-picker-calendar-day--day-in-month-or-selectable "
            "db-web-date-picker-calendar-day--selected-date db-web-date-picker-calendar-day--current-date",
        )
        next_day = current_day.next_sibling
        self.driver.find_element(By.XPATH, xpath_soup(next_day)).click()  # noqa

        accept_btn = self.driver.find_element(By.CSS_SELECTOR, "._button")
        accept_btn.click()

        search_btn = self.driver.find_element(
            By.CSS_SELECTOR,
            r"button.db-web-button:nth-child(3) > span:nth-child(1) > span:nth-child(1)",
        )

        search_btn.click()
        sleep(3)

        self.driver.find_element(
            By.CSS_SELECTOR,
            ".db-web-switch-list__button-container--align-top > span:nth-child(2)",
        ).click()
        sleep(3)


class DriverError(Exception):
    """Invalid or missing driver object."""


if __name__ == "__main__":
    pass
