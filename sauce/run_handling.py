import polars as pl
from . import config
from typing import Optional


class Run:

    """
    This loads in an entire run to memory to improve the
    speed at which Detector objects can be created. It also
    sorts the run by time stamps
    """

    def __init__(self, filename, primary_time_axis: Optional[str] = None):
        self.filename = filename
        if ".csv" in filename:
            self.data = pl.read_csv(filename)
        if ".parquet" in filename:
            self.data = pl.read_parquet(filename)
        if ".feather" in filename:
            self.data = pl.read_ipc(filename)
        if not primary_time_axis:
            primary_time_axis = config.default_time_axis
        self.data = self.data.sort(by=primary_time_axis)
