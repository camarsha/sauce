import polars as pl
from typing import Union


class Scalers:
    def __init__(self, filename):
        """
        Initialize a new instance of Scalers with the given filename.

        :param filename: The name of the file to be loaded.
        Should have a file extension of either .csv, .parquet or .feather.

        :return: None

        """
        self.filename = filename
        if ".csv" in filename:
            self.data = pl.read_csv(filename)
        if ".parquet" in filename:
            self.data = pl.read_parquet(filename)
        if ".feather" in filename:
            self.data = pl.read_ipc(filename)

    def sum(self, channel=None):
        temp = self.data.sum().to_numpy()[0]
        if channel is not None:
            return temp[channel]
        return temp
