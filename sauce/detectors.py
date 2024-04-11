"""
This file helps map the data to actual detectors and group them.

-Caleb Marshall, Ohio University 2022
"""

from numba.core.compiler import Option
import numpy as np
from matplotlib.path import Path
from .run_handling import Run
from . import config
import numba as nb
import polars as pl
from typing import Optional


@nb.njit
def referenceless_event_sort(times, build_window):
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
        name,
        primary_energy_axis=None,
        primary_time_axis=None,
    ):
        # must initialize the dataframe first to stop recursion error
        self.name = name
        self.primary_energy_axis = (
            primary_energy_axis
            if primary_energy_axis
            else config.default_energy_axis
        )
        self.primary_time_axis = (
            primary_time_axis if primary_time_axis else config.default_time_axis
        )
        self.data = pl.DataFrame()
        self._coin = True
        # Used by the context manager to assign a copy of data during the
        # context block and then update data afterwards.
        self.temp_data = None

    def find_hits(self, run_data, **kwargs):
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
        self.data = self.data.sort(by=self.primary_time_axis)
        return self

    def _hits_from_run(self, run_obj, **kwargs):
        # pull the relevant data
        return (
            run_obj.data.lazy()
            .filter(**kwargs)
            .drop([k for k, _ in kwargs.items()])
            .collect()
        )

    def _hits_from_str(self, run_str, **kwargs):
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

    def _axis_cond(self, axis):
        if axis == None:
            return self.primary_energy_axis
        else:
            return axis

    def _time_axis_cond(self, axis):
        if axis == None:
            return self.primary_time_axis
        else:
            return axis

    def apply_threshold(self, threshold, axis=None):
        axis = self._axis_cond(axis)
        self.data = self.data.filter(self.data[axis] > threshold)
        return self

    def apply_cut(self, cut, axis=None):
        axis = self._axis_cond(axis)
        self.data = self.data.filter(
            (self.data[axis] > cut[0]) & (self.data[axis] < cut[1])
        )
        return self

    def apply_poly_cut(self, cut2d):
        """
        Apply a 2D polygon cut to the data. Gate info is
        found in Gate2D object found in sauce.gates
        """
        points = cut2d.points
        x_axis = cut2d.x_axis
        y_axis = cut2d.y_axis

        poly = Path(points, closed=True)
        results = poly.contains_points(self.data[[x_axis, y_axis]])
        self.data = self.data.filter(results)
        return self

    def hist(self, lower, upper, bins, axis=None, centers=True):
        """
        Return a histrogram of the given axis.
        """
        axis = self._axis_cond(axis)

        counts, bin_edges = np.histogram(
            self.data[axis], bins=bins, range=(lower, upper)
        )
        # to make fitting data
        if centers:
            centers = bin_edges[:-1]
            return centers, counts
        else:
            return counts, bin_edges

    def __getitem__(self, item):
        return self.data.__getitem__(item)

    def __setitem__(self, item, value):
        self.data = self.data.with_columns(pl.lit(value).alias(item))
        return self.data

    def __invert__(self):
        self._coin = False
        return self

    def get_coin(self):
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

    def copy(self):
        """Copy data from detector into new detector instance.

        :returns: Copied instance of detector

        """
        new_det = Detector(self.name)
        new_det.data = self.data.clone()
        return new_det

    def tag(self, tag, tag_name="tag"):
        """Create a tag column in the dataframe.
        Examples could be run number, a simple index, or
        any other desired information.

        :param tag:
        :param tag_name:
        :returns:

        """
        self.data = self.data.with_columns(pl.lit(tag).alias(tag_name))
        return self

    def build_referenceless_events(self, build_window, axis=None):
        """Assign event numbers to the detector
        based on just the detectors hits. Also
        give the multiplicity of the event
        :param build_window: build window in ns.
        :returns:
        """
        time_axis = self._time_axis_cond(axis)
        evt_id = referenceless_event_sort(
            self.data[time_axis].to_numpy(), build_window
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

    def save(self, filename, file_type="parquet"):
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

    def load(self, filename):
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

    def counts(self):
        """Returns the number of rows in the data frame"""
        return len(self.data)

    def __len__(self):
        return len(self.data)


def detector_union(name, *dets, on="evt_ts"):
    """Union different detectors if into a
    new detector called "name"

    :param name: string, new detector name
    :returns: Detector object

    """
    new_det = Detector(name)
    new_det.data = pl.concat([d.data.lazy() for d in dets]).sort(on).collect()
    return new_det
