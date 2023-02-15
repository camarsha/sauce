import modin.pandas as pd
import tables as tb
import numpy as np
import numba as nb
from . import detectors


class Run:

    """
    The Lena version of sauce is much simpler at the
    moment due to the mdpp16 being simpler than pxi16.
    """

    def __init__(self, filename, mode="r", load=True):
        self.filename = filename
        self.df = pd.read_csv(filename)
        self.is_sorted = False
