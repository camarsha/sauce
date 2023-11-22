import polars as pl


class Run:

    """
    The Lena version of sauce is much simpler at the
    moment due to the mdpp16 being simpler than pxi16.
    """

    def __init__(self, filename, mode="r", load=True):
        self.filename = filename
        if ".csv" in filename:
            self.data = pl.read_csv(filename)
        if ".parquet" in filename:
            self.data = pl.read_parquet(filename)
        if ".feather" in filename:
            self.data = pl.read_ipc(filename)
