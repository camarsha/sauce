import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
import os


def hist2d(x, y, **kwargs):
    """
    This is so that 2d histograms can
    be generated uniformly in style
    """
    plt.hist2d(
        x, y, cmin=1, cmap="viridis", bins=1024, range=[[0, 32000], [0, 32000]]
    )


def add_runs(run_list):
    """
    Adds several run together into a single dataframe with a "global"
    event index
    """
    total = []
    max_index = 0

    for ele in run_list:
        ele["event"] = ele["event"] + max_index
        total.append(ele)
        max_index = ele["event"].max()

    df = pd.concat(total, ignore_index=True)
    return df


def position(x, y, **kwargs):
    plt.hist2d(
        x, y, cmin=1, cmap="viridis", bins=[32, 32], range=[[0, 32], [0, 32]]
    )


def eff(det1, det2):
    """
    Just a basic measure of efficiency, where number of
    events in det1 is compared to those in det2
    """
    e_1 = float(len(det1.data))
    e_2 = float(len(det2.data))
    return e_1 / e_2


def gate2d(x, y, points, bins=[1024, 300]):
    fig, ax = plt.subplots()
    ax.hist2d(x, y, bins=bins, cmin=1, range=[[0, x.max() + 5], [0, 35000]])
    path = Path(points, closed=True)
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


def find_adjacent(dssd):
    """Given a dssd detector that
    has defined multiplicity, select multiplicity
    two events and find which ones are
    adjacent.

    :param dssd: DSSD object
    :returns: data frame

    """
    temp = (
        dssd[dssd["multiplicity"] == 2]
        .groupby("local_event")["strip"]
        .transform("diff")
    )
    temp.iloc[::2] = temp.iloc[1::2]
    temp = np.abs(temp)
    return dssd[dssd["multiplicity"] == 2][temp == 1.0]
