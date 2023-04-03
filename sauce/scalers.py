import polars as pl


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
            self.df = pl.read_csv(filename).to_pandas()  # x5 faster
        if ".parquet" in filename:
            self.df = pl.read_parquet(filename).to_pandas()  # x15 faster
        if ".feather" in filename:
            self.df = pl.read_ipc(filename).to_pandas()  # x15 faster
        self.is_sorted = False
