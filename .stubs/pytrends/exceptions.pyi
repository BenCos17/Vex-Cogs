"""
This type stub file was generated by pyright.
"""

import requests

class ResponseError(Exception):
    """Something was wrong with the response from Google"""

    response: requests.Response
    def __init__(self, message, response) -> None: ...