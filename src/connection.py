import pathlib
from typing import Optional

import openpyxl
import pandas as pd


class Connection:
    def __init__(
        self,
        origin: str,
        destination: str,
        outward_journey: pd.DataFrame,
        inward_journey: Optional[pd.DataFrame] = None,
    ):
        """
        A connection object handling file interactions.
        """
        self.origin = origin
        self.destination = destination
        outward_journey.insert(
            1, "best", outward_journey.iloc[:, 1:].min(axis="columns")
        )
        if inward_journey is not None:
            inward_journey.insert(
                1, "best", inward_journey.iloc[:, 1:].min(axis="columns")
            )
        self.outward_journey = outward_journey
        self.inward_journey = inward_journey

    def to_excel(self, path):
        sheet_name = f"{self.origin} -> {self.destination}"
        path = pathlib.Path(path).resolve()
        if not path.exists():
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                wb: openpyxl.Workbook = writer.book
                wb.create_sheet(sheet_name)
        with pd.ExcelWriter(
            path, engine="openpyxl", mode="a", if_sheet_exists="overlay"
        ) as writer:
            self.outward_journey.to_excel(writer, sheet_name=sheet_name)
            self.inward_journey.to_excel(
                writer,
                sheet_name=sheet_name,
                startcol=self.outward_journey.shape[1] + 1,
            )

    @property
    def return_trip(self):
        return self.inward_journey is not None
