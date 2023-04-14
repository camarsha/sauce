import pandas as pd
import polars as pl


class Run:

    """
    The Lena version of sauce is much simpler at the
    moment due to the mdpp16 being simpler than pxi16.
    """

    def __init__(self, filename, mode="r", load=True):
        self.filename = filename
        if ".csv" in filename:
            self.df = pl.read_csv(filename).to_pandas()  # x5 faster
        if ".parquet" in filename:
            self.df = pl.read_parquet(filename).to_pandas()  # x15 faster
        if ".feather" in filename:
            self.df = pl.read_ipc(filename).to_pandas()  # x15 faster

        # sort the timestamps
        self.df = self.df.sort_values(by="evt_ts")
