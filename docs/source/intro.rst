################
*sauce* a primer
################

:code:`sauce` is a python package that serves as a data pipeline
for low-energy nuclear physics data. It has a few key assumptions
about the data that you have to deal with:

1) It can easily fit into your computers physical memory.
2) It has been converted into a very specific h5 file format
   (i.e via evth5_)

   .. _evth5: https://github.com/dubiousbreakfast/evth5
3) Data is timestamped from a digital data acquisition system.

Data that meets these 3 criteria is what :code:`sauce` is targeted towards.
So, let's start.


Import the package...

.. code-block:: python

   import sauce

You can use *sauce* to write standalone scripts, but the recommended use case,
especially for exploratory analysis is with a *read-eval-print loop* (REPL) running. One of
the primary motivators for *sauce's* design was to break out of the *write compile run*
workflow that makes `event building`_ and `gating`_ live separately from operations that can
be performed on histograms (fitting, plotting, etc.). Instead of creating an event loop that sorts your
data into histograms, you are looking at all hits in every channel in the system and correlating them however
you wish, and at anytime you can change how you group separate hits and apply gates and cuts. My point will become
clearer in a moment.

Loading Data
============

Before anything useful can be done with our data we need to load it.
*sauce* has limited support at this time for out-of memory analysis,
meaning if you want to do that route you will typically suffer from
data that loads an order of magnitude slower. A single run file can
be loaded into memory via the :code:`sauce.run_handling.Run` class.
First create a run object:

.. code-block:: python

   run = sauce.Run("h5-filename.h5")

Usually, this will take a little bit, but even for large files (:math:`> 2` GB) load times should be less than a minute or two.
Once you have the :code:`run` object you have all of the hits recorded by the DAQ and they have been time-ordered in a pandas DataFrame.
If you care to look at this information, you can access it under :code:`run.df`:.

Make A Detector
===============

The heart of *sauce* is the :code:`sauce.Detector` class. The intention is to put just a bit of wrapping around pandas DataFrame's to make
common tasks as painless as possible. An instance of :code:`Detector` can be histogrammed, gated on, and calibrated with its methods. Nearly
every other class or function in *sauce* is designed to work on :code:`Detector` objects and many return new :code:`Detector` objects.

So with the :code:`Run` object in hand from the last section, we can start making detectors:

.. code-block:: python

   run = sauce.Run("h5-filename.h5") # create an instance of Run that holds the data you care about
   det = sauce.Detector(0, 0, 10, "my_det") # We need the crate, module, channel, and name of the detector.
   det.find_events(run) # This pulls all of the hits in the specified crate, module, channel and puts them into det.data

The underlying DataFrame can be accessed using :code:`__getitem()`, so if we want to return the energy column we would just write
:code:`det["energy"]`. Histogramming of a :code:`Detector` can be done at anytime:

.. code-block:: python

   lower = 0
   upper = 32000
   bins = 4096
   det.hist(lower, upper, bins)



Event Building
==============

Looking at the hits of a single detector is of course useful, but
rarely the quantity of interest for an analysis. Here we assume that our data is a product of a *trigger less* digital data acquisition system. Under this assumption, any hit in any channel will be recorded, regardless of what is happening in the other channels. Relationships between channels will need to be specified via an *event builder*, and this *event builder* will, necessarily, have to be implemented in software.

*sauce* has two approaches to event building that can invoked at will:

* A simple function to group a set of hits into equal length bins. A build window is started by the earliest
  hit, regardless of channel, and all subsequent hits are grouped to that event.

* A more complex class that creates disjoint build windows from a set of reference timestamps.
   
It requires a mix and match of these event building techniques to cover common use cases. The simple approach is often suitable for a single physical detector that is readout through multiple channels (i.e DSSD, Gi Clover, position sensitive detectors). In *sauce* the simple approach can be invoked on a :code:`Detector` instance:

.. code-block:: python

   det.local_events(500) # instance of detector from above, 500 is 500 ns build window.
 
After invoking this method, :code:`det` will have two new columns in its DataFrame: "local_event" and "multiplicity". Now each hit can be associated with an event number (starting from 0) and the multiplicity column tell you how many total hits belong to that event number (i.e fall within the 500 ns build window).

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
   coin.add_detector(det1)
   coin.add_detector(det2)

   det_12 = coin[det1, det2] # the __getitem__ call builds a new detector that has coincident events from det1 and det2 using the event builder

For this particular case :code:`Coincident` is overkill, but with a more complex system it allows you to add as many detectors as needed, and then at will create a new detector that has only the coincidences that you are interested in. If we had two more detectors, :code:`det3` and :code:`det4`, we could do the following:

.. code-block:: python

   coin.add_detector(det3)
   coin.add_detector(det4)

   det34 = coin[det3, det4] # events that have both det3 and det4 in them (events are still referencing timestamps from det1)
   det24 = coin[det2, det4] # events that have both det2 and det4
   det1234 = coin[det1, det2, det3, det4] # events that have every detector present

		
Gating
======


