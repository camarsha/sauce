"""
This file helps map the data to actual detectors and group them.

-Caleb Marshall, Ohio University 2022
"""

import numpy as np
from matplotlib.path import Path
from numpy.typing import NDArray
from .run_handling import Run
from . import config
from . import gates
import numba as nb
import polars as pl
from typing import Any, Optional, Type, Sequence, Union, List, Tuple
from typing_extensions import Self


@nb.njit
def referenceless_event_sort(times, build_window) -> NDArray[np.float64]:
    """Produce an array with event number.

    The event number is based on a simple build
    window starting from the earliest event.
    :param times:
    :param build_window:
    :returns:

    """
    t_i = times[0]
    t_f = t_i + build_window
    event = 0
    event_number = np.empty(len(times))
    event_number[:] = np.nan

    for i in range(len(times)):
        tc = times[i]

        if tc >= t_i and tc < t_f:
            event_number[i] = event
        else:
            t_i = tc
            t_f = tc + build_window
            event += 1
            event_number[i] = event
    return event_number


class Detector:
    """Class to hold data relevant to the specific channel."""

    def __init__(
        self,
        name: str,
        primary_energy_col: Optional[str] = None,
        primary_time_col: Optional[str] = None,
    ):
        # must initialize the dataframe first to stop recursion error
        self.name = name
        self.primary_energy_col = (
            primary_energy_col
            if primary_energy_col
            else config.default_energy_col
        )
        self.primary_time_col = (
            primary_time_col if primary_time_col else config.default_time_col
        )
        self.data = pl.DataFrame()
        self._coin = True
        self.livetime = 1.0

    def find_hits(self, run_data: Union[str, Run], **kwargs) -> Self:
        """
        After more usage, I think it is useful to either
        load the entire run (detailed analysis) or
        pull from disk just the specific data.

        As such this function is now more general, and
        calls two other methods to select the data depending
        on whether a Run object is passed or a path to an h5 file.
        """

        if isinstance(run_data, Run):
            self.data = self._hits_from_run(run_data, **kwargs)
        elif isinstance(run_data, str):
            self.data = self._hits_from_str(run_data, **kwargs)
        else:
            print("Only Run objects or csv_file paths accepted!")
        self.data = self.data.sort(by=self.primary_time_col)
        return self

    def _hits_from_run(self, run_obj: Run, **kwargs) -> pl.DataFrame:
        # pull the relevant data
        return (
            run_obj.data.lazy()
            .filter(**kwargs)
            .drop([k for k, _ in kwargs.items()])
            .collect()
        )

    def _hits_from_str(self, run_str: str, **kwargs) -> pl.DataFrame:
        # pull the data
        temp_scan = None
        if ".csv" in run_str:
            temp_scan = pl.scan_csv(run_str)
        elif ".parquet" in run_str:
            temp_scan = pl.scan_parquet(run_str)
        elif ".feather" in run_str:
            temp_scan = pl.scan_ipc(run_str)
        else:
            raise (FileNotFoundError)
        return (
            temp_scan.filter(**kwargs)
            .drop([k for k, _ in kwargs.items()])
            .collect(streaming=True)
        )

    def _col_cond(self, col: Optional[str]) -> str:
        if col == None:
            return self.primary_energy_col
        else:
            return col

    def _time_col_cond(self, col: Optional[str]) -> str:
        if col == None:
            return self.primary_time_col
        else:
            return col

    def apply_threshold(
        self, threshold: float, col: Optional[str] = None
    ) -> Self:
        col = self._col_cond(col)
        self.data = self.data.filter(self.data[col] > threshold)
        return self

    def apply_cut(
        self, cut: Sequence[float], col: Optional[str] = None
    ) -> Self:
        col = self._col_cond(col)
        self.data = self.data.filter(
            (self.data[col] > cut[0]) & (self.data[col] < cut[1])
        )
        return self

    def apply_poly_cut(self, cut2d: gates.Gate2D) -> Self:
        """
        Apply a 2D polygon cut to the data. Gate info is
        found in Gate2D object found in sauce.gates
        """
        points = cut2d.points
        x_col = cut2d.x_col
        y_col = cut2d.y_col

        poly = Path(points, closed=True)
        results = poly.contains_points(self.data[[x_col, y_col]])
        self.data = self.data.filter(results)
        return self

    def hist(
        self,
        lower: float,
        upper: float,
        bins: int,
        col: Optional[str] = None,
        centers: bool = True,
        norm: float = 1.0,
    ) -> Tuple[NDArray[Any], NDArray[Any]]:
        """
        Return a histrogram of the given col.
        """
        col = self._col_cond(col)

        counts, bin_edges = np.histogram(
            self.data[col], bins=bins, range=(lower, upper)
        )
        # to make fitting data
        if centers:
            temp_centers = bin_edges[:-1]
            return temp_centers, counts / norm
        else:
            return counts / norm, bin_edges

    def __getitem__(self, item: str) -> pl.Series:
        return self.data.__getitem__(item)

    def __setitem__(self, item: str, value: Any) -> pl.DataFrame:
        self.data = self.data.with_columns(pl.lit(value).alias(item))
        return self.data

    def __invert__(self) -> Self:
        self._coin = False
        return self

    def get_coin(self) -> bool:
        """Returns the current value of
        coin, and then resets it to True.

        If you are constructing anti-coincidences, this
        makes sure that you will always have self.__coin = True
        unless you have just called the ~ operator.

        :returns:

        """

        val = self._coin
        self._coin = True
        return val

    def copy(self) -> Self:
        """Copy data from detector into new detector instance.

        :returns: Copied instance of detector

        """
        new_det = Detector(self.name)
        new_det.data = self.data.clone()
        return new_det

    def tag(self, tag: Any, tag_name: str = "tag") -> Self:
        """Create a tag column in the dataframe.
        Examples could be run number, a simple index, or
        any other desired information.

        :param tag:
        :param tag_name:
        :returns:

        """
        self.data = self.data.with_columns(pl.lit(tag).alias(tag_name))
        return self

    def build_referenceless_events(
        self, build_window: float, col: Optional[str] = None
    ) -> Self:
        """Assign event numbers to the detector
        based on just the detectors hits. Also
        give the multiplicity of the event
        :param build_window: build window in ns.
        :returns:
        """
        time_col = self._time_col_cond(col)
        evt_id = referenceless_event_sort(
            self.data[time_col].to_numpy(), build_window
        )
        col_name = "event_" + self.name
        # add event id column
        self.data = self.data.with_columns(
            pl.lit(evt_id).cast(pl.UInt64).alias(col_name)
        )
        # we create a column of 1s, count them (i.e make a sum) over the groups of local events
        # finally puttin the results in multiplicity and modifying the original data frame.
        self.data = self.data.with_columns(
            pl.lit(1, dtype=pl.UInt16).alias("multiplicity")
        )  # this needs to be a separate step because pl.lit needs to turn into a column first

        self.data = (
            self.data.lazy()
            .with_columns(
                pl.col("multiplicity")
                .count()
                .over(col_name)
                .alias("multiplicity")
            )
            .collect()
        )
        return self

    def save(self, filename, file_type: str = "parquet") -> Self:
        if file_type == "parquet":
            self.data.write_parquet(filename)
        elif file_type == "feather":
            self.data.write_ipc(filename)
        elif file_type == "csv":
            self.data.write_csv(filename)
        else:
            print(
                "File type {} not recongnized. Try: parquet, feather, or csv.".format(
                    file_type
                )
            )
        return self

    def load(self, filename) -> Self:
        file_type = filename.split(".")[-1]

        if file_type == "parquet":
            self.data = pl.read_parquet(filename)
        elif file_type == "feather":
            self.data = pl.read_ipc(filename)
        elif file_type == "csv":
            self.data = pl.read_csv(filename)
        else:
            print(
                "File type {} not recongnized. Try: parquet, feather, or csv.".format(
                    file_type
                )
            )
        return self

    def counts(self) -> int:
        """Returns the number of rows in the data frame"""
        return len(self.data)

    def __len__(self) -> int:
        return len(self.data)


def detector_union(
    name: str, *dets: Detector, on: Optional[str] = None
) -> Detector:
    """Union different detectors if into a
    new detector called "name"

    :param name: string, new detector name
    :returns: Detector object

    """
    if not on:
        on = config.default_time_col
    new_det = Detector(name)
    new_det.data = pl.concat([d.data.lazy() for d in dets]).sort(on).collect()
    return new_det
