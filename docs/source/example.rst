===================
Coincidence Example
===================

    :Author: caleb

.. contents::



1 Determining the Activity of a :math:`^{241} \text{Am}` Source
---------------------------------------------------------------

Here is an example to get the feel of a simple experiment that uses the
event building capabilities of *sauce* and shows some
of the potential pitfalls of building off of arbitrary detector hits.  

Radioactive sources with known radioactivity are valuable tools
for nuclear physics experiments. They offer simple checks of
detector efficiencies and/or solid angles. Determining the absolute activity
of a source requires excellent control over the geometry if a single detector
with a defined solid angle is to be used. However, if a given decay emits several
decay products (:math:`\gamma \text{-} \gamma`, :math:`\alpha \text{-} \gamma`, :math:`\beta \text{-}\gamma`)
then a coincidence detection scheme can be employed to remove the impact of geometric uncertainties.

:math:`^{241} \text{Am}` is commonly used as both an :math:`\alpha \text{-source}` and :math:`\gamma \text{-souce}`. Absolute activity can be determined from the :math:`\alpha \text{,}` :math:`\gamma \text{,}` and coincident decay rates (denoted :math:`R_{\alpha}`, :math:`R_{\gamma}`, and :math:`R_{\alpha\gamma}`, respectively)
The *observed* :math:`\alpha \text{-decay}` rate for N transitions is given by:



.. math::

    R_{\alpha} = \sum_{i=1}^{N} D_i \epsilon_i,

where :math:`D_i` and :math:`\epsilon_i` are the *true* decay rate and detector efficiency (including geometric efficiency) for the :math:`i^{\text{th}}` :math:`\alpha \text{-transition}`.
For a surface barrier or equivalent silicon detector :math:`\epsilon_i` is independent of :math:`i`. Likewise for the :math:`\gamma \text{-decays}`:




.. math::

    R_{\gamma} = \sum_{i=1}^{N} E_i \epsilon^{\prime}_i,

where :math:`E_i` labels the :math:`\gamma` transition rate for the :math:`\gamma \text{-rays}`. An energy cut in the :math:`\gamma \text{-spectrum}` can reduce the above equation to: :math:`R_{\gamma} = E_1 \epsilon^{\prime}_1`. Under this condition, the coincidence rate is determined from the smallest decay rate either :math:`D_i` or :math:`E_i`, which for :math:`^{241} \text{Am}` is :math:`E_1 \approx 0.36`.
The *observed* coincidence decay rate is then:


.. math::

    R_{\alpha\gamma} = E_1 \epsilon^{\prime}_1 \epsilon_1.

By combining the observed decay rates we can find a relation to the true decay rates



.. math::

    \frac{R_{\alpha} R_{\gamma}}{R_{\alpha \gamma}} = \frac{E_1 \epsilon^{\prime}_1  \sum_{i=1}^{N} D_i \epsilon}{E_1 \epsilon^{\prime}_1 \epsilon_1} = \sum_{i=1}^{N} D_i.

The three observed decay rates can be used to determine the absolute decay rate
of the :math:`^{241}\text{Am}` sample [1]_ .

2 Experiment and Spectrum Generation
------------------------------------

`241Am-coin-data.h5 <./example-data/>`_ data file provided was taken with a PIPS detector located in a vacuum chamber located in close geometry to a NIST calibrated :math:`^{241}\text{Am}` source with activity :math:`1.230(15)` :math:`\mu\text{Ci}`. Outside the vacuum chamber, facing the source, was a CeBr (dimensions?) detector. The vacuum interface was a :math:`1` cm thick piece of acrylic.

The channel map for this data is:

.. table::

    +----------+-------+--------+---------+
    | Detector | Crate | Module | Channel |
    +----------+-------+--------+---------+
    | Si       |     0 |      2 |       0 |
    +----------+-------+--------+---------+
    | CeBr     |     0 |      2 |       1 |
    +----------+-------+--------+---------+

To find the decay rates :math:`R_{\alpha}`, :math:`R_{\gamma}`, and :math:`R_{\alpha\gamma}` we need to generate
three detectors in *sauce*. The singles data is trivial to load:

.. code:: python

    import sauce
    import matplotlib.pyplot as plt

    run = sauce.Run("./example-data/241Am-coin-data.h5")

    si = sauce.Detector(0, 2, 0, "si")
    si.find_events(run)
    cebr = sauce.Detector(0, 2, 1, "cebr")
    cebr.find_events(run)

    eb = sauce.EventBuilder() # create the event builder class
    eb.add_timestamps(si) # use only the silicon detector to build events
    eb.create_build_windows(-1000, 1000) # For each silicon hit group everything +/- 1000 ns.

    print(eb.livetime) # This number gives you the percentage of silicon event that are kept.

    coin = sauce.Coincident(eb) # create the coincidence object from the event builder
    # Add the hit information
    coin.add_detector(si) 
    coin.add_detector(cebr)

    si_cebr_coin = coin[si, cebr] # creates a new detector object with the coincident events 
    si_cebr_coin.data["dt"] = si_cebr_coin["time_cebr"] - si_cebr_coin["time_si"] # To construct

      # silicon singles, adc range is roughly ~2^15
    plt.step(*si.hist(0, 32768, 500))
    plt.show()
    # cebr singles
    plt.step(*cebr.hist(0, 32768, 500))
    plt.show()
    # timing spectra, axis argument can switch from default "energy" column
    plt.step(*si_cebr_coin.hist(-1000, 1000, 2000, axis='dt'))

Coincidence data requires an event building scheme:

.. code:: python

    eb = sauce.EventBuilder() # create the event builder class
    eb.add_timestamps(si) # use only the silicon detector to build events
    eb.create_build_windows(-1000, 1000) # For each silicon hit group everything +/- 1000 ns.

    print(eb.livetime) # This number gives you the percentage of silicon event that are kept.

    coin = sauce.Coincident(eb) # create the coincidence object from the event builder
    # Add the hit information
    coin.add_detector(si) 
    coin.add_detector(cebr)

    si_cebr_coin = coin[si, cebr] # creates a new detector object with the coincident events 
    si_cebr_coin.data["dt"] = si_cebr_coin["time_cebr"] - si_cebr_coin["time_si"] # To construct a timing spectra just subtract the two columns.

Histograms can be generated for all the spectra:

.. code:: python

    # silicon singles, adc range is roughly ~2^15
    plt.step(*si.hist(0, 32768, 500))
    plt.show()
    # cebr singles
    plt.step(*cebr.hist(0, 32768, 500))
    plt.show()
    # timing spectra, axis argument can switch from default "energy" column
    plt.step(*si_cebr_coin.hist(-1000, 1000, 500, axis='dt'))
    plt.show()

The technique outlined in Section 1 needed the :math:`\gamma\text{-spectrum}` to be gated on the :math:`60\text{-keV}` transition, which is the most prominent peak in the CeBr spectrum (roughly around channel :math:`1300`). The low energy tail on the peak comes mostly from the attenuation of the :math:`\gamma\text{-rays}` through the acrylic window on the vacuum chamber. To remove the impact
of this tail and to give us the most signal to background, we gate on the peak region
:math:`(1262, 1474)`. :meth:`sauce.Detector` defines two gating functions: :meth:`sauce.Detector.apply_cut` for 1D gates and :meth:`sauce.Detector.apply_poly_cut` for 2D gates. 2D gates are not necessary for
this case, so we can simply plug in the above (open) interval into the two detectors that
need an energy cut:

.. code:: python

    # cuts are exclusive on both sides of the interval.
    cebr.apply_cut((1262, 1474)) # applied to energy axis by default
    si_cebr_coin.apply_cut((1262, 1474), axis="energy_cebr") # when multiple axis have the same name the detector name is append with an underscore.

It is also a good idea to apply an energy cut on the silicon detector, which has some signs of pile up due to the close source geometry.

.. code:: python

    si.apply_cut((0, 3100)) # get rid of the pile up
    si_cebr_coin.apply_cut((0, 3100), axis="energy_si") # get rid of the pile up 

Of course these cuts could (and probably should) be done before event building, and if they are
then :code:`si_cebr_coin` will already take into account the energy discrimination. 

.. caution::

    These methods are destructive! The detector DataFrame will be modified.

Technically this is the end of *sauce's* job. We can now freely generate every spectra and plug into any analysis package or environment that we want.

3 Analysis and Results.
-----------------------

Note the exponential decay seen in the coincidence timing spectrum. Pick your favorite way to fit
an exponential and determine the half-life. I get: :math:`70.3(33)` ns compared to the most recent compiled value of :math:`67.2(7)` ns  [2]_ .

Next we need to estimate the background in the CeBr spectrum for both singles and coincidence. A simple sideband estimation on the high energy side of the :math:`60\text{-keV}` peak yieldes: :math:`19.5` counts/bin, or roughly :math:`195` counts. Background corrected, we have the following counts:



.. math::

    C_{\alpha} = 1719400(1300) \\
    C_{\gamma} = 120700(350) \\
    C_{\alpha\gamma} = 2460(50) \\

The total time can be found from the earliest hit in the silicon detector:

.. code:: python

      total_time = (
        si.data.iloc[-1]["time_raw"] - si.data.iloc[0]["time_raw"]
    ) / 1e9  # nanoseconds to seconds

Finally:


.. math::

    D_{tot} = \frac{C_{\alpha} C_{\gamma}}{C_{\alpha\gamma}} \frac{1}{\Delta t} \frac{1}{37000} = 1.274(25) \, \mu \text{Ci}

where the error is statistical only and neglects the background error estimate. A conservative estimate would be that the total error is on the order of :math:`5 \%`, giving excellent agreement with the quoted NIST value. 


.. [1] Angular correlation between the decaying particles complicates this simple picture, but it is on the order of a few percent for decays from the :math:`60\text{-keV}` state.  

.. [2] Coming from `NNDC <https://www.nndc.bnl.gov/nudat3/getdataset.jsp?nucleus=237Np&unc=NDS>`_. Note the value given in this documentation and its uncertainties are statistical only.
