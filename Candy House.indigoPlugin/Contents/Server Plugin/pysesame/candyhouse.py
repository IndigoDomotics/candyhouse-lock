"""
Module to manage CANDY HOUSE API.
"""
import json
import subprocess
import indigo

API_URL = 'https://api.candyhouse.co/v1'
API_LOGIN_ENDPOINT = '/accounts/login'
API_SESAME_LIST_ENDPOINT = '/sesames'
API_AUTH_HEADER = 'X-Authorization'


class CandyHouseAccount(object):
    """Representation of a CANDY HOUSE account."""

    api_url = API_URL
    auth_token = None
    email = None
    password = None
    session = None

    class response(object):
        pass


    def curl_helper(self, headers, payload, url):
        hdrs = []    
        for key, value in headers.iteritems():
            hdrs.append('-H')
            hdrs.append(key + ': ' + value)

        if payload is not None:         
            pl = ['-X', 'POST', '-d', payload]
        else:
            pl = []

        try:            
            proc = subprocess.Popen(['curl','-s','-w','\n%{http_code}'] + hdrs + pl + [url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()

            if proc.returncode == 0:
                outl = out.split('\n')
                r = self.response()
                r.text = ''.join(outl[0:-1])
                r.status_code = int(outl[-1])
                #indigo.server.log(message="Code: " + str(r.status_code))
                #indigo.server.log(message="Text: " + r.text)
                return r
        except:
            pass

        indigo.server.log(message="Error executing Curl command to contact CandyHouse server.", isError=True)

        return None


    def login(self, email=None, password=None, timeout=5):
        """Log in to CANDY HOUSE account. Return True on success."""
        if email is not None:
            self.email = email
        if password is not None:
            self.password = password

        url = self.api_url + API_LOGIN_ENDPOINT
        data = json.dumps({'email': self.email, 'password': self.password})
        headers = {}
        headers['Content-Type'] = 'application/json'

        response = self.curl_helper(headers, data, url)
        if response is not None:
            if response.status_code == 200:
                self.auth_token = json.loads(response.text)['authorization']
                return True
            else:
                indigo.server.log(message="Error logging in.  Received response code %d." % response.status_code, isError=True)
                return False

        indigo.server.log(message="Error logging in.", isError=True)
        return False


    def request(self, method, endpoint, payload=None, timeout=5):
        """Send request to API."""
        url = self.api_url + endpoint
        headers = {}
        data = None

        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload)
            
        if self.auth_token is not None:
            headers[API_AUTH_HEADER] = self.auth_token
            response = self.curl_helper(headers, data, url)            
            if response.status_code != 401:
                return response

        indigo.server.log(message="Renewing auth token")
        if not self.login(timeout=timeout):
            return None

        # Retry  request
        headers[API_AUTH_HEADER] = self.auth_token
        return self.curl_helper(headers, data, url)            


    @property
    def sesames(self):
        """Return list of Sesames."""
        response = self.request('GET', API_SESAME_LIST_ENDPOINT)
        if response is not None and response.status_code == 200:
            return json.loads(response.text)['sesames']

        indigo.server.log(message="Unable to get Sesames", isError=True)
        return []

        
