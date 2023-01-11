###################
Coincidence Example
###################

Determining the Activity of a :sup:`241`\ Am Source
=====================================================

Here is an example to get the feel of a simple experiment that uses the
event building capabilities of *sauce* and shows some
of the potential pitfalls of building off of arbitrary detector hits.  

Radioactive sources with known radioactivity are valuable tools
for nuclear physics experiments. They offer simple checks of
detector efficiencies and/or solid angles. Determining the absolute activity
of a source requires excellent control over the geometry if a single detector
with a defined solid angle is to be used. However, if a given decay emits several
decay products (:math:`\gamma \text{-} \gamma`, :math:`\alpha \text{-} \gamma`, :math:`\beta \text{-} \gamma`)
then a coincidence detection scheme can be employed to remove the impact of geometric uncertainties.

:sup:`241`\ Am is commonly used as both an :math:`\alpha`\ -source and :math:`\gamma`\ -source. Absolute activity can be determined from the :math:`\alpha`\ , :math:`\gamma`\ -decay\ , and :math:`\alpha\ \text{-} \gamma`\ decay rates (denoted :math:`R_{\alpha}`, :math:`R_{\gamma}`, and :math:`R_{\alpha\ \text{-} \gamma}`, respectively)
The total :math:`\alpha`\ -decay rate for N transitions is given by:

.. math::
   R_{\alpha} = \sum_{i}^{N} D_i \epsilon_i,
     
where :math:`D_i` and :math:`\epsilon_i` are the decay rate and detector efficiency for the :math:`i^{\text{th}}` :math:`\alpha`\ -transition.
For a surface barrier or equivalent silicon detector :math:`\epsilon_i` is independent of :math:`i` and :math:`\approx 1`. Likewise for the
:math:`\gamma`\ -decays:

      
.. math::
   R_{\gamma} = \sum_{i}^{N} E_i \epsilon^{\prime}_i,
     
where it must be emphasized that :math:`E_i` labels the gamma transition for the :math:`\gamma`\ -rays. A coincidence count rate can be found
that assumes we have selected only a single :math:`\gamma`\ -transition yielding :math:`R_{\gamma} = E_1 \epsilon^{\prime}_1`. Under this condition

.. math::
   R_{\alpha\ \text{-} \gamma} = 
