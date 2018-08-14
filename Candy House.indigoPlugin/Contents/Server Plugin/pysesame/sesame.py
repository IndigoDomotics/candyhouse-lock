"""
Module to control Sesame devices.
"""
import json

API_SESAME_ENDPOINT = '/sesames/{}'
API_SESAME_CONTROL_ENDPOINT = '/sesames/{}/control'


class Sesame(object):
    """Representation of a Sesame device."""

    account = None
    use_cached_state = False
    _device_id = None
    _nickname = None
    _is_unlocked = False
    _api_enabled = False
    _battery = -1

    def __init__(self, account, state):
        """Initialise the Sesame device."""
        self.account = account
        self._device_id = state['device_id']
        self._nickname = state['nickname']
        self._is_unlocked = state['is_unlocked']
        self._api_enabled = state['api_enabled']
        self._battery = state['battery']
        self.use_cached_state = False


    @property
    def device_id(self):
        """Return the Sesame ID."""
        return self._device_id

    @property
    def nickname(self):
        """Return the Sesame nickname."""
        return self._nickname

    @property
    def is_unlocked(self):
        """Return True if Sesame is unlocked, else False."""
        return self._is_unlocked

    @is_unlocked.setter
    def is_unlocked(self, value):
        """Set is_unlocked property."""
        if value:
            self.unlock()
        else:
            self.lock()

    @property
    def api_enabled(self):
        """Return True if Sesame is API-enabled, else False."""
        return self._api_enabled

    @property
    def battery(self):
        """Return Sesame battery status as an integer between 0 and 100"""
        return self._battery

    def lock(self):
        """Lock the Sesame. Return True on success, else False."""
        endpoint = API_SESAME_CONTROL_ENDPOINT.format(self.device_id)
        payload = {'type': 'lock'}
        response = self.account.request('POST', endpoint, payload=payload)
        if response is None:
            return False
        if response.status_code == 200 or response.status_code == 204:
            return True
        return False

    def unlock(self):
        """Unlock the Sesame. Return True on success, else False."""
        endpoint = API_SESAME_CONTROL_ENDPOINT.format(self.device_id)
        payload = {'type': 'unlock'}
        response = self.account.request('POST', endpoint, payload=payload)
        if response is None:
            return False
        if response.status_code == 200 or response.status_code == 204:
            return True
        return False
