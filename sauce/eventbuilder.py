import pandas as pd
import numpy as np
import numba as nb
from . import detectors

"""
The philosophy of SAUCE is to build meaningful correlations between 
detector events. This is done by mimicking the way a traditional ADC gate
would work. In other words:

1) Define the detectors that will "open" the gate
2) Look for all coincidences within a given dT.

What we don't want are arbitrary build windows based on higher rate detectors.
  
"""


def get_closest(array, values):
    """

    Find the indices of elements in array that lie closest to
    values.

    Note, arrays should be sorted!

    :param array:
    :param values:

    """

    # make sure array is a numpy array
    array = np.array(array)

    # get insert positions
    idxs = np.searchsorted(array, values, side="left")

    # find indexes where previous index is closer
    prev_idx_is_less = (idxs == len(array)) | (
        np.fabs(values - array[np.maximum(idxs - 1, 0)])
        < np.fabs(values - array[np.minimum(idxs, len(array) - 1)])
    )
    idxs[prev_idx_is_less] -= 1

    return idxs


@nb.njit
def reduce_intervals(low, high):
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
def find_coincident_events(A, B, C):
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
def assign_event(hit_index, lower, upper, data):
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
    for i in range(len(hit_index)):
        hit_num = hit_index[i]
        l = lower[hit_num]
        h = upper[hit_num]
        for j in range(start_index, len(data)):
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
        self.lower = None
        self.upper = None
        self.pre_reduced_len = 0.0
        self.reduced_len = 0.0
        self.timestamps = []
        self.event_numbers = []

    def add_timestamps(self, det, time_axis="time_raw"):
        """Add the timestamps of the given detector to
        the event builder logic.

        :param det: instance of detectors.Detector
        :returns:

        """
        if isinstance(det, detectors.Detector):
            timestamps = det.data[time_axis].to_numpy()
        elif isinstance(det, pd.Series):
            timestamps = det.to_numpy()
        self.timestamps = np.concatenate((self.timestamps, timestamps))
        # make sure it is sorted
        self.timestamps = np.sort(self.timestamps)

    def create_build_windows(self, low, high):
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

        low_stamps = self.timestamps + low
        high_stamps = self.timestamps + high

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

    def calc_livetime(self):
        """Calculate the livetime of the eventbuilder instance, and
        assign the result to self.livetime

        :returns:

        """
        self.livetime = self.reduced_len / self.pre_reduced_len

    def filter_data(self, det, time_axis="time_raw"):
        """
        For the given detector, look at each event and see if it can be assigned
        to an event based on the time stamp array. Keep only the hit with the earliest timestamp.
        Modifies detector in place.

        :param det: instance of detectors.Detector
        :returns: time filtered detectors.Detector

        """
        det_times = det.data[time_axis].to_numpy()

        # get indices of events that contain at least one of the detectors time stamps
        mask = find_coincident_events(self.lower, self.upper, det_times)
        hit_index = np.arange(len(self.lower))[mask]

        # assign event numbers to every event (if no event give NaN)
        event_number = assign_event(
            hit_index, self.lower, self.upper, det_times
        )
        det.data["event"] = event_number

        # drop duplicate events keep first timestamp
        det.data = det.data.drop_duplicates("event", keep="first")

        return det


def same_event(det1, det2):
    """

    Sorting based on event number, defined by the event builder
    time window. In theory function can be applied as many times as
    needed/desired.

    :param det1: instance of detectors.Detector
    :param det2: instance of detectors.Detector
    :returns: instance of detectors.Detector

    """
    # These errors are if we have already called the function once
    # If that is the case, then the column names will not exist
    try:
        df1 = det1.data.rename(
            columns={
                "energy": "energy" + "_" + det1.name,
                "time": "time" + "_" + det1.name,
            }
        ).copy()
    except KeyError:
        df1 = det1.data

    df1 = df1.dropna(subset=["event"])

    try:
        df2 = det2.data.rename(
            columns={
                "energy": "energy" + "_" + det2.name,
                "time": "time" + "_" + det2.name,
            }
        )
    except KeyError:
        df2 = det2.data

    df2 = df2.dropna(subset=["event"])

    df3 = pd.merge(
        df1, df2, on="event", suffixes=("_" + det1.name, "_" + det2.name)
    )
    new_det = detectors.Detector(0, 0, 0, det1.name + "_" + det2.name)
    new_det.data = df3
    return new_det


class Coincident:
    def __init__(self, ref_det_eb):
        """This has been reworked to because the
        old version was half broken.
        We want to have a lighter weight object, so
        ideally you just call coin[det1, det2, det3]
        and get out what you
        want, instead of a huge dataframe being stored.
        :param eb: instance of EventBuilder
        """
        self.eb = None
        self.data = pd.DataFrame({"event": ref_det_eb.event_numbers.copy()})
        self.eb = ref_det_eb
        self.det_names = []
        self.det_columns = {}

    def _detector_or_name(self, det):
        if isinstance(det, detectors.Detector):
            name = det.name
        else:
            name = det
        if name not in self.det_names:
            raise Exception(name + " is not in this object.")
        return name

    def add_detectors(self, *dets):
        """Add a several detectors data to the coincidence object.
        :param det: an instance of detector.Detector
        :param columns: If none, we take all non-empty columns
        :returns:
        """

        # now add them to the data frame
        for det in dets:
            # update classes list, so we know what we got
            if det.name in self.det_names:
                print(det.name + " is already in coincidence object, skipping.")
                continue
            else:
                self.det_names.append(det.name)

            # create a copy so we can destructively alter every thing
            det = det.copy()
            self.eb.filter_data(det)

            # rename the detector columns
            new_names = {}
            # store the column names for easy retrieval later
            self.det_columns[det.name] = []

            for ele in det.data.columns:
                # if this was already produced from a coin object we don't need
                # to rename
                try:
                    name_check = ele.split("_")[1]
                    if name_check == det.name:
                        self.det_columns[det.name].append(
                            ele
                        )  # put unaltered name in
                        continue  # we already have a column that denotes the detector
                except IndexError:
                    pass  # default case, name is unaltered at this point
                if ele != "event":
                    new_name = ele + "_" + det.name
                    new_names[ele] = new_name
                    self.det_columns[det.name].append(
                        new_name
                    )  # we don't care about event

            # rename and merge
            self.data = pd.merge(
                self.data,
                det.data.rename(columns=new_names),
                on="event",
                how="left",
            )

    def _get_column(self, det, axis):
        name = axis + "_"
        name += self._detector_or_name(det)
        return self.data[name]

    def _get_detector_columns(self, det):
        name = self._detector_or_name(det)
        columns = self.det_columns[name]
        return columns

    def _column_mask(self, det, axis):
        if det.coin:
            return ~self.data[axis].isnull()
        else:
            # reset the coin slot so we can use ~ again
            det.coin = not det.coin
            # return the anticoincidences
            return self.data[axis].isnull()

    def create_intersection(self, *dets):
        """Given all these detectors return
        a detector that has all of the coincident values.
        :returns:
        """
        truth_series = []
        total_name = ""
        columns = ["event"]

        for d in dets:
            # make a name like dssd_ic_another_....
            if total_name:
                total_name += "_"

            temp_name = self._detector_or_name(d)
            cols = self._get_detector_columns(d)
            if not d.coin:
                # not coincident, don't extract columns
                total_name += "!" + temp_name
            else:
                total_name += temp_name
                # all the columns needed
                columns += cols

            # Just grab the first column
            truth_series.append(self._column_mask(d, cols[0]))

        total = np.logical_and.reduce(truth_series)
        new_det = detectors.Detector(0, 0, 0, total_name)
        new_det.data = self.data.loc[total][columns]
        return new_det

    def __getitem__(self, key):
        """I want to be able to select detectors based on Coincidence[det]
        like syntax. These get items will return detector objects.
        """
        # return a new instance of Coincidence
        if isinstance(key, tuple):
            return self.create_intersection(*key)
        if isinstance(key, slice):
            return self.data[key]
        return self.create_intersection(key)
