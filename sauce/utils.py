import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
import numpy as np


def step(x, y, **step_kwargs):
    """The default step drawing will appear incorrect
    without where = "post". Note that the data is the
    same in both cases, this is just to make the plots appear correct.

    :param x:
    :param y:
    :returns:

    """
    plt.step(x, y, where="post", **step_kwargs)


def hist2d(x, y, **kwargs):
    """
    This is so that 2d histograms can
    be generated uniformly in style
    """
    plt.hist2d(x, y, cmin=1, cmap="viridis", **kwargs)


def eff(det1, det2):
    """
    Just a basic measure of efficiency, where number of
    events in det1 is compared to those in det2
    """
    e_1 = float(len(det1.data))
    e_2 = float(len(det2.data))
    return e_1 / e_2


def gate2d(x, y, gate, **kwargs):
    fig, ax = plt.subplots()
    ax.hist2d(x, y, **kwargs)
    path = Path(gate.points, closed=True)
    patch = patches.PathPatch(path, facecolor="r", alpha=0.2)
    ax.add_patch(patch)


def save_txt_spectrum(filename, x, y):
    """Save binned data to a two column text file.

    :param filename:
    :param x:
    :param y:
    :returns:

    """
    with open(filename, "w") as f:
        for i, j in zip(x, y):
            f.write(str(i) + "      " + str(j) + "\n")
