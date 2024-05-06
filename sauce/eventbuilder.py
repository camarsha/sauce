from numpy.typing import NDArray
import polars as pl
import numpy as np
import numba as nb
from . import detectors
from . import config
from typing import Any, Optional, Union, List, Tuple
from typing_extensions import Self


@nb.njit
def reduce_intervals(low: NDArray[Any], high: NDArray[Any]) -> List[Any]:
    """
    Help create arrays that define
    closed, disjoint intervals.
    Index i takes us through the high values
    Index j takes us through the low values
    :param low: array of low timestamps
    :param high: array of high timestamps
    """
    reject = []

    i = 0
    j = 1

    while i < len(high) and j < len(low):
        h = high[i]
        l = low[j]
        if l <= h:
            reject.append(j)
            j += 1
        elif l > h:
            i = j
            j += 1

    return reject


@nb.njit
def find_coincident_events(
    A: NDArray[Any], B: NDArray[Any], C: NDArray[Any]
) -> NDArray[np.bool_]:
    """
    taken from: https://stackoverflow.com/questions/43382056/detect-if-elements-are-within-pairs-of-interval-limits
    Find element of A and B such that C is C>=A and C<=B
    """

    # Use searchsorted and look for
    m_AB = np.searchsorted(C, A, "left") != np.searchsorted(
        C, B, "right"
    )  # masks for the timestamp array
    return m_AB


@nb.njit
def assign_event_index(
    hit_index: NDArray[np.int_],
    lower: NDArray[Any],
    upper: NDArray[Any],
    data,
):
    """
    :param hit_index:
    :param lower:
    :param upper:
    :param data:
    :returns:
    """
    event_number = np.empty(len(data))
    event_number[:] = np.nan
    start_index = 0
    len_data = len(data)
    for i in range(len(hit_index)):
        hit_num = hit_index[i]
        l = lower[hit_num]
        h = upper[hit_num]
        for j in range(start_index, len_data):
            if l <= data[j] <= h:
                event_number[j] = hit_num
            elif data[j] < l:
                event_number[j] = np.nan
            elif data[j] > h:
                start_index = j
                break
    return event_number


class EventBuilder:
    """
    Construct a builder that takes a
    low and high time value, constructs intervals,
    removes overlapping intervals, then filters
    other data based on these intervals.
    Build a time stamp array by adding detector times
    with self.add_timestamps. Eventbuilder will make
    sure this array is time ordered.
    After all desired detectors have been added
    disjoint build windows are created using
    self.create_build_windows(low, high)
    low and high are the time before and after
    these events that are considered for correlations.
    They are in units of nanoseconds.
    """

    def __init__(self):
        self.lower: NDArray[Any] = np.empty(0)
        self.upper: NDArray[Any] = np.empty(0)
        self.pre_reduced_len = 0.0
        self.reduced_len = 0.0
        self.timestamps: NDArray[Any] = np.empty(0)
        self.event_numbers = []

    def add_timestamps(
        self, det: Union[detectors.Detector, pl.Series], axis=None
    ):
        """Add the timestamps of the given detector to
        the event builder logic.
        :param det: instance of detectors.Detector
        :returns:
        """
        axis = axis if axis else config.default_time_axis
        if isinstance(det, detectors.Detector):
            timestamps = det.data[axis].to_numpy()
        elif isinstance(det, pl.Series):
            timestamps = det.to_numpy()
        else:
            raise TypeError(
                "Must pass either a sauce.Detector or polars.Series instance."
            )
        self.timestamps = np.concatenate((self.timestamps, timestamps))
        # make sure it is sorted
        self.timestamps = np.sort(self.timestamps)
        return self

    def create_build_windows(self, low: float, high: float) -> Self:
        """Call after all timestamps have been added. Method
        then constructs disjoint intervals with in
        :param low: lower bound of coincident window in nanoseconds
        :param high: upper bound of coincident window in nanoseconds
        :returns:
        """
        # The low, high arguments are now signed, so check that they make sense
        if high <= low:
            raise Exception(
                "Invalid build window, high limit is less than low limit."
            )
        if self.timestamps.shape == 0:
            raise Exception(
                "No timestamps have been added. Call EventBuilder.add_timestamps first."
            )

        low_stamps = np.asarray(self.timestamps) + low
        high_stamps = np.asarray(self.timestamps) + high

        self.pre_reduced_len = len(self.timestamps)

        drop_indx = reduce_intervals(low_stamps, high_stamps)

        low_stamps = np.delete(low_stamps, drop_indx)
        high_stamps = np.delete(high_stamps, drop_indx)

        # combine (if there was any data before) and sort
        self.lower = low_stamps
        self.upper = high_stamps

        self.reduced_len = len(self.lower)
        self.event_numbers = np.arange(self.reduced_len)

        self.calc_livetime()

        if self.livetime < 0.90:
            print("Warning dead time is greater than 10%!!")
        return self

    def calc_livetime(self) -> float:
        """Calculate the livetime of the eventbuilder instance, and
        assign the result to self.livetime
        :returns:
        """
        self.livetime = self.reduced_len / self.pre_reduced_len
        return self.livetime

    def assign_events_to_detector_and_drop(
        self, det: detectors.Detector, axis: Optional[str] = None
    ) -> detectors.Detector:
        """
        For the given detector, look at each event and see if it can be assigned
        to an event based on the time stamp array. Keep only the hit with the earliest timestamp.

        :param det: instance of detectors.Detector
        :returns: time filtered detectors.Detector
        """

        if self.lower.shape == 0 or self.upper.shape == 0:
            raise Exception(
                "No build windows have been constructed. Call EventBuilder.create_build_windows first."
            )

        axis = axis if axis else config.default_time_axis
        det_times = det.data[axis].to_numpy()

        before_len = len(det.data)

        # get indices of events that contain at least one of the detectors time stamps
        mask = find_coincident_events(self.lower, self.upper, det_times)
        hit_index = np.arange(len(self.lower))[mask]

        # assign event numbers to every event (if no event give NaN)
        event_number = assign_event_index(
            hit_index, self.lower, self.upper, det_times
        )

        det.data = (
            det.data.lazy()
            .with_columns(pl.lit(event_number).alias("event"))
            .filter(~pl.col("event").is_nan())
            .unique(subset=["event"], keep="first", maintain_order=True)
            .with_columns(pl.col("event").cast(pl.Int64))
            .collect()
        )

        # drop duplicate events keep first timestamp
        after_len = len(det.data)
        det.livetime = after_len / before_len

        return det


class Coincident:
    def __init__(self, eb: EventBuilder):
        self.data: pl.DataFrame = pl.DataFrame(
            {"event": eb.event_numbers.copy()}
        )
        self.eb: EventBuilder = eb

    def create_coincidence(
        self, *dets: detectors.Detector, coincident_detector_name=None
    ) -> detectors.Detector:
        if not coincident_detector_name:
            coincident_detector_name = "_".join([det.name for det in dets])
        new_det = detectors.Detector(coincident_detector_name)
        # now we do a inner merge on all the data
        new_det.data = self.data.clone()
        for det in dets:
            temp_det = self.eb.assign_events_to_detector_and_drop(det.copy())
            temp_det.data = temp_det.data.rename(
                {
                    col: col + "_" + temp_det.name
                    for col in temp_det.data.columns
                    if col != "event"
                }
            )
            # we do inner joins unless we asked for anti-coincidence
            how_type = "anti" if not det.get_coin() else "inner"
            new_det.data = new_det.data.join(
                temp_det.data,
                on="event",
                how=how_type,
            ).sort(by="event")

        return new_det

    def __getitem__(
        self, key: Union[detectors.Detector, Tuple[detectors.Detector]]
    ) -> detectors.Detector:
        """Create specific coincident detectors using a syntax of Coincidence[det]

        :param key: Detector objects.

        """
        # return a new instance of Coincidence
        if isinstance(key, tuple):
            return self.create_coincidence(*key)
        return self.create_coincidence(key)
