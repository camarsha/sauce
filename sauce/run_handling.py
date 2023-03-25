import pandas as pd
import polars as pl


class Run:

    """
    The Lena version of sauce is much simpler at the
    moment due to the mdpp16 being simpler than pxi16.
    """

    def __init__(self, filename, mode="r", load=True):
        self.filename = filename
        self.df = pl.read_csv(filename).to_pandas()  # x5 faster
        self.is_sorted = False
