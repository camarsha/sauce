import numpy as np

# import pandas as pd
import modin.pandas as pd
from matplotlib.path import Path
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import json
from . import detectors


class Gate2D:
    def __init__(self, x_axis, y_axis):
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.points = []

    def save(self, gate_name):
        if ".json" not in gate_name:
            gate_name += ".json"
        with open(gate_name, "w") as f:
            json.dump(self._convert_to_dic(), f)

    def _convert_to_dic(self):
        return {
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "points": self.points,
        }

    @staticmethod
    def load(filename):
        with open(filename, "r") as f:
            dic = json.load(f)
        return Gate2D._convert_from_dic(dic)

    @staticmethod
    def _convert_from_dic(dic):
        temp = Gate2D(dic["x_axis"], dic["y_axis"])
        temp.points = dic["points"][:]
        return temp


class CreateGate2D(Gate2D):
    def __init__(self, det, x_axis, y_axis, **hist2d_kwargs):
        Gate2D.__init__(self, x_axis, y_axis)
        x = det.data[x_axis]
        y = det.data[y_axis]
        self.fig, self.ax = plt.subplots()
        self.ax.hist2d(x, y, **hist2d_kwargs)
        self.ax.set_title("Click to set gate, press enter to finish")
        self.cid = plt.connect("button_press_event", self.on_click)
        self.cid2 = plt.connect("key_press_event", self.on_press)
        plt.show()

    def on_click(self, event):
        x, y = event.xdata, event.ydata
        if event.inaxes:
            # add a point on left click
            if event.button == 1:
                print(x, y)
                self.points.append((x, y))
                self.drawing_logic()
                plt.draw()
            elif event.button == 3:
                self.points.pop()
                self.drawing_logic()
                print("Deleting last point")
                plt.draw()

    def on_press(self, event):
        if event.key == "enter":
            plt.disconnect(self.cid)
            self.points.append(self.points[0])
            self.patch_update(closed=True, facecolor="r", alpha=0.2)
            plt.draw()
            print(self.points)
            return self.points

    def patch_update(self, closed=False, facecolor="none", alpha=1.0):
        path = Path(self.points, closed=closed)
        patch = patches.PathPatch(path, facecolor=facecolor, alpha=alpha)
        self.ax.add_patch(patch)

    def drawing_logic(self):
        if len(self.points) == 1:
            self.ax.scatter(self.points[0][0], self.points[0][1])
        elif len(self.points) >= 2:
            self.patch_update()
        else:
            pass
