"""
This module holds global configurations that are
referenced in all of sauce. For example the default
time or energy axis. The purpose is to allow additional
flexability on how the data file are defined.

-Caleb Marshall UNC/TUNL, 2024
"""

default_time_axis: str = "evt_ts"
default_energy_axis: str = "adc"


def set_default_energy_axis(axis_name: str):
    global default_energy_axis
    default_energy_axis = axis_name


def set_default_time_axis(axis_name: str):
    global default_time_axis
    default_time_axis = axis_name
