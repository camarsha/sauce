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
   

 
   
Gating
======

And here
