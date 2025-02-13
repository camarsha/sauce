from numpy import load
from .detectors import *
from .eventbuilder import *
from . import utils
from . import gates
from .gates import Gate2D, Gate1D, Gate2DFromHist2D, Gate1DFromHist1D
from .run_handling import *
from .scalers import Scalers
from .config import set_default_energy_col
from .config import set_default_time_col
import os
import sys

# this looks for sauce_rc.py in two places, first
# the current directory and second the users home directory
this_directory = os.getcwd()
user_directory = os.path.expanduser("~")
if os.path.exists(this_directory + "/sauce_rc.py"):
    print("sauce_rc.py found in directory, loading...")

    import sauce_rc as rc

    print("Done.")
elif os.path.exists(user_directory + "/sauce_rc.py"):
    print("sauce_rc.py found in home directory, loading...")
    sys.path.insert(0, user_directory)
    import sauce_rc as rc

    # clean up the path
    sys.path.remove(user_directory)
    print("Done.")
