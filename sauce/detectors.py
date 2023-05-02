"""
This file helps map the data to actual detectors and group them.

-Caleb Marshall, Ohio University 2022
"""

import numpy as np
from matplotlib.path import Path
from .run_handling import Run
import numba as nb
import pandas as pd
import polars as pl


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

    def __init__(self, name, primary_axis="adc"):
        # must initialize the dataframe first to stop recursion error
        self.name = name
        self.primary_axis = "adc"
        self.data = None
        self.coin = True

    def find_hits(self, run_data, module_id, channel):
        """
        After more usage, I think it is useful to either
        load the entire run (detailed analysis) or
        pull from disk just the specific data.

        As such this function is now more general, and
        calls two other methods to select the data depending
        on whether a Run object is passed or a path to an h5 file.
        """

        if isinstance(run_data, Run):
            self._hits_from_run(run_data, module_id, channel)
        elif isinstance(run_data, str):
            self._hits_from_str(run_data, module_id, channel)
        else:
            print("Only Run objects or csv_file paths accepted!")
        # drop useless columns and sort the timestamps
        self.data = (
            self.data.drop(columns=["module", "channel"])
            .reset_index(drop=True)
            .sort_values(by="evt_ts")
        )

    def _hits_from_run(self, run_obj, module, channel):
        df = run_obj.df

        # pull the relevant data
        self.data = df.loc[
            (df["module"] == module) & (df["channel"] == channel)
        ]

    def _hits_from_str(self, run_str, module, channel):
        # pull the data
        if ".csv" in run_str:
            self.data = (
                pl.scan_csv(run_str)
                .filter(
                    (pl.col("module") == module)
                    & (pl.col("channel") == channel)
                )
                .collect(streaming=True)
                .to_pandas()
            )
        if ".parquet" in run_str:
            self.data = (
                pl.scan_parquet(run_str)
                .filter(
                    (pl.col("module") == module)
                    & (pl.col("channel") == channel)
                )
                .collect(streaming=True)
                .to_pandas()
            )

        if ".feather" in run_str:
            self.data = (
                pl.scan_ipc(run_str)
                .filter(
                    (pl.col("module") == module)
                    & (pl.col("channel") == channel)
                )
                .collect(streaming=True)
                .to_pandas()
            )

    def _axis_cond(self, axis):
        if axis == None:
            return self.primary_axis
        else:
            return axis

    def apply_threshold(self, threshold, axis=None):
        axis = self._axis_cond(axis)
        self.data = self.data[self.data[axis] > threshold]

    def apply_cut(self, cut, axis=None):
        axis = self._axis_cond(axis)
        self.data = self.data.loc[
            (self.data[axis] > cut[0]) & (self.data[axis] < cut[1])
        ]

    def apply_poly_cut(self, cut2d, gate_name=None):
        """
        Apply a 2D polygon cut to the data. Gate info is
        found in Gate2D object found in sauce.gates
        """
        points = cut2d.points
        x_axis = cut2d.x_axis
        y_axis = cut2d.y_axis

        poly = Path(points, closed=True)
        results = poly.contains_points(self.data[[x_axis, y_axis]])
        self.data = self.data[results]

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

    def __setitem__(self, item):
        return self.data.__setitem__(item)

    def __invert__(self):
        self.coin = not self.coin
        return self

    def copy(self):
        """Copy data from detector into new detector instance.

        :returns: Copied instance of detector

        """
        new_det = Detector(self.name)
        new_det.data = self.data.copy(deep=True)
        return new_det

    def tag(self, tag, tag_name="tag"):
        """Create a tag column in the dataframe.
        Examples could be run number, a simple index, or
        any other desired information.

        :param tag:
        :param tag_name:
        :returns:

        """
        self.data[tag_name] = tag

    def build_referenceless_events(self, build_window, time_axis="evt_ts"):
        """Assign event numbers to the detector
        based on just the detectors hits. Also
        give the multiplicity of the event
        :param build_window: build window in ns.
        :returns:
        """
        evt_id = referenceless_event_sort(
            self.data[time_axis].to_numpy(), build_window
        )
        col_name = "event_" + self.name
        self.data[col_name] = evt_id
        self.data["multiplicity"] = 1
        self.data["multiplicity"] = self.data.groupby("local_event")[
            "multiplicity"
        ].transform("count")


def detector_union(name, *dets, by="evt_ts"):
    """Union different detectors if into a
    new detector called "name"

    :param name: string, new detector name
    :returns: Detector object

    """
    frame = [d.data for d in dets]
    new_det = Detector(name)
    new_det.data = pd.concat(frame, ignore_index=True).sort_values(by=by)
    return new_det
