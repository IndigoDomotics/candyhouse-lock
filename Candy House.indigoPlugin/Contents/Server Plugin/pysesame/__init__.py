"""
Python API to control Sesame smart locks.
  This library was written by Albert Lee
  https://github.com/trisk/pysesame

  Modified by Travis to use curl instead of request
  to get around Python < 2.7.10 sslv3 error
"""

from .candyhouse import CandyHouseAccount
from .sesame import Sesame


def account():
    return CandyHouseAccount()


def get_sesames(account):
    """Return list of available Sesame objects."""
    sesames = []

    for sesame in account.sesames:
        sesames.append(Sesame(account, sesame))

    return sesames

