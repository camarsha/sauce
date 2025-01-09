import numpy as np
from matplotlib.path import Path
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import json
import polars as pl
import time


def maybe_close_polygon(points):
    """Close a polygon if it is not already closed.
    Returns a fresh list.

    :param points: list of tuples
    :returns: list of tuples

    """
    new_points = points[:]
    if new_points[-1] != new_points[0]:
        new_points.append(new_points[0])
    return new_points


class Gate1D:
    def __init__(self, col: str, points=None) -> None:
        self.col: str = col
        if points is not None:
            self.points = points[:]
        else:
            self.points = []

    def _convert_to_dic(self):
        return {
            "col": self.col,
            "points": self.points,
        }

    def save(self, gate_name):
        if ".json" not in gate_name:
            gate_name += ".json"
        with open(gate_name, "w") as f:
            json.dump(self._convert_to_dic(), f)

    @staticmethod
    def load(filename):
        with open(filename, "r") as f:
            dic = json.load(f)
        return Gate1D._convert_from_dic(dic)

    @staticmethod
    def _convert_from_dic(dic):
        temp = Gate1D(dic["col"], dic["points"][:])
        return temp


class Gate2D:
    def __init__(self, x_col, y_col, points=None):
        self.x_col = x_col
        self.y_col = y_col
        if points is not None:
            self.points = maybe_close_polygon(points)
        else:
            self.points = []

    def save(self, gate_name):
        if ".json" not in gate_name:
            gate_name += ".json"
        with open(gate_name, "w") as f:
            json.dump(self._convert_to_dic(), f)

    def _convert_to_dic(self):
        return {
            "x_col": self.x_col,
            "y_col": self.y_col,
            "points": self.points,
        }

    @staticmethod
    def load(filename):
        with open(filename, "r") as f:
            dic = json.load(f)
        return Gate2D._convert_from_dic(dic)

    @staticmethod
    def _convert_from_dic(dic):
        temp = Gate2D(dic["x_col"], dic["y_col"], dic["points"][:])
        return temp


class CreateGate2D(Gate2D):
    """
    Likely to depreciate this.
    """

    def __init__(self, det, x_col, y_col, **hist2d_kwargs):
        Gate2D.__init__(self, x_col, y_col)
        x = det.data[x_col].to_numpy()
        y = det.data[y_col].to_numpy()
        if "cmin" not in hist2d_kwargs:
            hist2d_kwargs["cmin"] = 1
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


class Gate2DFromHist2D(Gate2D):
    def __init__(self, x: pl.Series, y: pl.Series, **hist2d_kwargs):
        x_col = x.name
        y_col = y.name
        Gate2D.__init__(self, x_col, y_col)
        if "cmin" not in hist2d_kwargs:
            hist2d_kwargs["cmin"] = 1
        self.fig, self.ax = plt.subplots()
        self.ax.hist2d(x.to_numpy(), y.to_numpy(), **hist2d_kwargs)
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


class Gate1DFromHist1D(Gate1D):
    def __init__(self, x: pl.Series, bins=None, range=None, **hist1d_kwargs):
        # quicker to histogram once and draw with step.
        col = x.name
        Gate1D.__init__(self, col)
        if "histtype" not in hist1d_kwargs:
            hist1d_kwargs["histtype"] = "step"
        self.hist_kwargs = hist1d_kwargs
        self.fig, self.ax = plt.subplots()
        self.ax.hist(x.to_numpy(), bins, range, **hist1d_kwargs)
        self.ax.set_title("Click to set gate.")
        self.cid = plt.connect("button_press_event", self.on_click)
        self.lines = []
        plt.show()

    def on_click(self, event):
        x, y = event.xdata, event.ydata
        if event.inaxes:
            # add a point on left click
            if event.button == 1:
                # you haven't appended the point yet,
                # so exit when this exits on what would be the third point
                if len(self.points) > 1:
                    return self.finish_up()
                else:
                    print(x)
                    self.points.append(x)
                    self.drawing_logic(x)
            elif event.button == 3:
                self.points.pop()
                self.ax.collections.pop()
                self.drawing_logic()
                print("Deleting last point")

    def finish_up(self):
        plt.disconnect(self.cid)
        plt.close()
        return self.points

    def drawing_logic(self, point=None):
        y_min = self.ax.get_ylim()[0]
        y_max = self.ax.get_ylim()[1] * 0.8

        if point is not None:
            self.ax.vlines(
                point,
                self.ax.get_ylim()[0],
                self.ax.get_ylim()[1] * 0.90,
                ls="--",
                color="k",
            )

        plt.draw()
