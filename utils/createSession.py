# utils/createSession.py

import requests
from requests.auth import HTTPBasicAuth
import getpass

def createSession(id):
    """Function creates a session for communication with IS VUT

    Args:
        id (_type_): BUT personal ID

    Returns:
        _type_: session 
    """
    s = requests.Session()
    password=getpass.getpass(prompt=f"Password (user {id}): ", stream=None)
    s.auth = HTTPBasicAuth(id, password)
    
    return s 