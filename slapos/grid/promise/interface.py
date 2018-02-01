# coding: utf-8
from zope.interface import Interface


class IPromise(Interface):
  """Base Promise interface."""

  def __init__(config):
    """
      @param config: Configurations needed to start the promise
    """

  def anomaly(self):
    """
      Called to detect if there is an anomaly.
      @return AnomalyResult object
    """

  def sense(self):
    """
      Run the promise code and store the result
      raise error, log error message, ... for failure
    """

  def test(self):
    """
      Test promise and say if problem is detected or not
      @return TestResult object
    """
