import modin.pandas as pd
import numpy as np
from . import detectors

"""
Stripped down version of the original, since mdpps already have events built in.
"""


class Coincident:
    def __init__(self, ref_det):
        """This class expands on the initial
        concept present in same_event(det1, det2).

        We start to build a hierarchical structure
        with the nodes being event number.

        :param eb: instance of EventBuilder

        """
        self.data = pd.DataFrame({"event": ref_det["event"].copy()})
        self.det_names = []

    def _detector_or_name(self, det):
        if isinstance(det, detectors.Detector):
            name = det.name
        else:
            name = det
        if name not in self.det_names:
            raise Exception(name + " is not in this object.")
        return name

    def add_detectors(self, *dets, columns=None):
        """Add a several detectors data to the coincidence object.

        :param det: an instance of detector.Detector
        :param columns: If none, we take all non-empty columns
        :returns:

        """
        for det in dets:
            det = det.copy()

            # update classes list, so we know what we got
            if det.name in self.det_names:
                raise Exception(
                    det.name + " is already in this coincidence object."
                )
            self.det_names.append(det.name)

            # Only pull the non-empty columns
            if not columns:
                columns = []
                for ele in det.data.columns:
                    try:
                        if np.any(det.data[ele]):
                            columns.append(ele)
                    except ValueError:
                        # These two quantities will continue to haunt me
                        if ele == "trace" or "qdc" in ele:
                            columns.append(ele)
                        else:
                            print("Not sure what to do with column:" + ele)

            # new names to identify with the specific detector
            new_names = {}
            for ele in columns:
                if det.name not in ele and ele != "event":
                    new_names[ele] = ele + "_" + det.name

            self.data = pd.merge(
                self.data,
                det.data[columns].rename(columns=new_names),
                on="event",
                how="left",
            )

    def _get_column(self, det, axis):
        name = axis + "_"
        name += self._detector_or_name(det)
        return self.data[name]

    def _get_detector_columns(self, det):
        name = self._detector_or_name(det)
        columns = [i for i in self.data.columns if name in i]
        return columns

    def _column_mask(self, det, axis):
        name = axis + "_"
        name += self._detector_or_name(det)
        return ~self.data[name].isnull()

    def create_intersection(self, *dets):
        """Given all these detectors return
        a detector that has all of the coincident values.

        :returns:

        """
        truth_series = []
        total_name = ""
        columns = []

        for d in dets:
            # make a name like dssd_ic_another_....
            if total_name:
                total_name += "_"
            total_name += self._detector_or_name(d)
            # all the columns needed
            columns += self._get_detector_columns(d)

            # I am assuming that adc is always a valid column
            truth_series.append(self._column_mask(d, "adc"))

        total = np.logical_and.reduce(truth_series)
        new_det = detectors.Detector(total_name)
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
