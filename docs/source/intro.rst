################
*sauce* a primer
################

:code:`sauce` is a python package that serves as a data pipeline
for low-energy nuclear physics data. It has a few key assumptions
about the data that you have to deal with:

1) It can easily fit into your computers physical memory.
2) It has been converted into csv, parquet, or feather.


The package can be install by cloning the repository and running:

.. code-block:: python

   pip install .
   
Python 3.9 through 3.12 have been tested.

   
After install the package just import it.

.. code-block:: python

   import sauce

User Configuration
==================
Note that upon importing :code:`sauce` it looks for a user configuration file :code`sauce_rc.py` in two places:

1) The current working directory.
2) If that is not found, it searches the users home directory.

:code:`sauce` assumes some column names by default these can be changed with:

.. code-block:: python
	
   sauce.sauce.config.set_default_energy_col("energy")      
   sauce.sauce.config.set_default_time_col("time")      

By default these are called, somewhat cryptically, "adc" for energy and "evt_ts" for time (it stands for event/timestamp). :code:`sauce_rc.py` can hold specific experimental information or anything else that will be needed for your particular analysis. 

You can use *sauce* to write standalone scripts, but the recommended use case,
especially for exploratory analysis is with a *read-eval-print loop* (REPL) running. One of
the primary motivators for *sauce's* design was to break out of the *write compile run*
workflow that makes event building and gating live separately from operations that can
be performed on histograms (fitting, plotting, etc.).

Loading Data
============

Before anything useful can be done with our data we need to load it.
*sauce* has limited support at this time for out-of memory analysis,
meaning if you want to do that route you will typically suffer from
data that loads an order of magnitude slower. A single run file can
be loaded into memory via the :code:`sauce.run_handling.Run` class.
First create a run object:

.. code-block:: python

   run = sauce.Run("filename.parquet")

Once you have the :code:`run` object you have all of the hits recorded by the DAQ and they have been time-ordered in a polars DataFrame.
If you care to look at this information, you can access it under :code:`run.data`.

Make A Detector
===============

The heart of *sauce* is the :code:`sauce.Detector` class. The intention is to put just a bit of wrapping around polars to make common tasks as painless as possible. An instance of :code:`Detector` can be histogrammed, gated on, and calibrated with its methods. Nearly
every other class or function in *sauce* is designed to work on :code:`Detector` objects and many return new :code:`Detector` objects.

So with the :code:`Run` object in hand from the last section, we can start making detectors:

.. code-block:: python

   run = sauce.Run("filename.parquet") # create an instance of Run that holds the data you care about
   det = sauce.Detector("my_det") # Detectors need names.
   det.find_hits(run, channel=channel) # This pulls all of the hits that have a given channel number.

The underlying DataFrame can be accessed using :code:`__getitem()`, so if we want to return the "adc" column we would just write
:code:`det["adc"]`. Histogramming of a :code:`Detector` can be done at anytime:

.. code-block:: python

   lower = 0
   upper = 32000
   bins = 4096
   det.hist(lower, upper, bins)

:code:`Detector.hist` defaults to the :code:`default_energy_col`. Each Detector object can set its own preferred column for methods to call:

.. code-block:: python
		
   det.primary_energy_col = "energy"
   det.primary_time_col = "time"

Now :code:`Detector.hist` would histogram the "energy" column by default.
   
Event Building
==============

Looking at the hits of a single detector is of course useful, but
rarely the quantity of interest for an analysis. Here we assume that our data is a product of a *trigger less* digital data acquisition system. Under this assumption, any hit in any channel will be recorded, regardless of what is happening in the other channels. Relationships between channels will need to be specified via an *event builder*, and this *event builder* will, necessarily, have to be implemented in software.

*sauce* has two approaches to event building that can invoked at will:

* A simple function to group a set of hits into equal length bins. A build window is started by the earliest
  hit, regardless of channel, and all subsequent hits are grouped to that event. This is called "referenceless" event building. 

* A more complex class that creates disjoint build windows from a set of reference timestamps. This is called "referenced" event building.
   
It requires a mix and match of these event building techniques to cover common use cases. The simple approach is often suitable for a single physical detector that is readout through multiple channels (i.e DSSSD or HPGe Clover). In *sauce* the simple approach can be invoked on a :code:`Detector` instance:

.. code-block:: python

   det.build_referenceless_events(500) # instance of detector from above, 500 ns build window.
 
After invoking this method, :code:`det` will have two new columns in its DataFrame: "event_my_det" and "multiplicity". Now each hit can be associated with an event number (starting from 0) and the multiplicity column tell you how many total hits belong to that event number (i.e fall within the 500 ns build window).

If you have two separate physical detectors (say a charged particle detector of some kind and a gamma detector), it is often the case that one of those will have a much lower count rate and you wish to find a hit in the other detector only if the lower rate detector has fired. The :code:`sauce.EventBuilder` class is built just for this scenario:

.. code-block:: python

   det1 # low count rate detector that has already been initialized with data
   det2 # high count rate detector

   eb = sauce.EventBuilder() # create the event builder object
   eb.add_timestamps(det1) # takes the data in the "time_raw" column and adds it to the object
   eb.create_build_windows(-500, 500) # Build windows 500 ns before and after the det1 hit.

At this stage we have an event builder that will *uniquely* associate events. What I mean is that if two hits in the reference detector overlap temporally, the later hit is dropped.
Once these disjoint windows are built and data that is filtered through the event builder will also have one hit kept (the earliest) and the rest dropped. Each event by construction can only
be associated with one hit in each detector.

The simplest way to start looking at correlations once you have an initialized event builder is to use the :code:`sauce.Coincident` class.

.. code-block:: python

   coin = sauce.Coincident(eb) # pass it the event builder instance
   det_12 = coin[det1, det2] # the __getitem__ call builds a new detector that has coincident events from det1 and det2 using the event builder

For this particular case :code:`Coincident` is overkill, but with a more complex system it allows you to add as many detectors as needed, and then at will create a new detector that has only the coincidences that you are interested in. If we had two more detectors, :code:`det3` and :code:`det4`, we could do the following:

.. code-block:: python


   det34 = coin[det3, det4] # events that have both det3 and det4 in them (events are still referencing timestamps from det1)
   det24 = coin[det2, det4] # events that have both det2 and det4
   det1234 = coin[det1, det2, det3, det4] # events that have every detector present
   det123_no_4 = coin[det1, det2, det3, ~det4] # ~ builds an anti-coincidence with det4 and the other 3 detectors.
   


