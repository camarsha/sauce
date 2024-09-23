from .detectors import *
from .eventbuilder import *
from . import utils
from . import gates
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
    import sauce_rc
elif os.path.exists(user_directory + "/sauce_rc.py"):
    sys.path.insert(0, user_directory)
    import sauce_rc

    # clean up the path
    sys.path.remove(user_directory)
