from .detectors import *
from .eventbuilder import *
from . import utils
from . import gates
from .run_handling import *
from .scalers import Scalers
from .config import set_default_energy_axis
from .config import set_default_time_axis
import os


this_directory = os.getcwd()
user_directory = os.path.expanduser("~")
print(f"Looking in {this_directory}")
if os.path.exists(this_directory + "/sauce_rc.py"):
    import sauce_rc
elif os.path.exists(user_directory + "/sauce_rc.py"):
    import sauce_rc
