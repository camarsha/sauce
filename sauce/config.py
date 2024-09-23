"""
This module holds global configurations that are
referenced in all of sauce. For example the default
time or energy column. The purpose is to allow additional
flexability on how the data file are defined.

-Caleb Marshall UNC/TUNL, 2024
"""

default_time_col: str = "evt_ts"
default_energy_col: str = "adc"


def set_default_energy_col(col_name: str):
    global default_energy_col
    default_energy_col = col_name


def set_default_time_col(col_name: str):
    global default_time_col
    default_time_col = col_name
