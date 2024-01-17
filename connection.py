import requests
from rich.console import Console
import json

class Connection:
    def __init__(self, socket, secret):
        self.url = socket
        self.secret = secret
        self.headers = {'Authorization': f'token {secret}'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.jpy_sessions = dict()
        self.con = Console()

    def get(self, path="api/contents"):
        return self.session.get(self.url + path).json()
    
    def list_running_jpy_sessions(self):
        sessions = list()
        for jpy_sess in self.get('api/sessions'):
            self.jpy_sessions[jpy_sess["id"]] = jpy_sess
            sessions.append(jpy_sess["id"])
        return sessions