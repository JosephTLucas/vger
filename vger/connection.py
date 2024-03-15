import requests
from rich.console import Console
import json
import urllib.parse
from typing import Dict
import rich
from datetime import datetime


class Connection:
    def __init__(self, socket="", secret=""):
        self.url: str = socket
        self.secret: str = secret
        self.headers: Dict = {"Authorization": f"token {secret}"}
        self.session: requests.Session = requests.Session()
        self.session.headers.update(self.headers)
        self.jpy_sessions: Dict = dict()
        self.con: Console = Console(record=True)
        self.jpy_terminals: Dict = dict()
        self.sessions = list()
        self.target = None
        self.model_paths = list()
        self.datasets = list()
        self.jobs = dict()
        self.menu = None
        self.first_time_in_menu = {
            "enumerate": True,
            "exploit": True,
            "exploit_attack": True,
            "persist": True,
        }

    def print_with_rule(self, text, category="Output", json=False):
        self.con.rule(f"[bold green]{category}")
        if json:
            self.con.print_json(text)
        else:
            try:
                self.con.print(text)
            except rich.errors.MarkupError:
                print(text)
        self.con.rule(f"[bold green]{datetime.now().strftime('%c')}")

    def get(self, path="api/contents"):
        return self.session.get(self.url + path).json()

    def post(self, path="api/contents"):
        return self.session.post(self.url + path).json()

    def list_running_jpy_sessions(self):
        sessions = list()
        for jpy_sess in self.get("api/sessions"):
            self.jpy_sessions[jpy_sess["id"]] = jpy_sess
            sessions.append(jpy_sess["id"])
        return sessions

    def list_running_jpy_terminals(self):
        terminals = list()
        for jpy_term in self.get("api/terminals"):
            self.jpy_terminals[jpy_term["name"]] = jpy_term["last_activity"]
            terminals.append(jpy_term["name"])
        return terminals

    def create_terminal(self):
        new_term = self.post("api/terminals")
        self.jpy_terminals[new_term["name"]] = new_term["last_activity"]
        return new_term

    def delete_terminal(self, terminal):
        self.session.delete(self.url + f"api/terminals/{terminal}")

    def list_dir(self, path):
        try:
            return self.get(f"api/contents/{urllib.parse.quote(path)}")
        except requests.exceptions.JSONDecodeError:
            return {"Error": "Invalid Path"}

    def upload(self, path, data):
        try:
            return self.session.put(
                self.url + f"api/contents/{urllib.parse.quote(path)}", data=data
            ).json()
        except requests.JSONDecodeError:
            return json.dumps(
                {"Error": "There is a problem with the specified file and/or path."}
            )

    def delete(self, path):
        return self.session.delete(
            self.url + f"api/contents/{urllib.parse.quote(path)}"
        )


class DumbConnection:
    """
    Pickle-serializable Connection for Python process spawning
    """

    def __init__(self, socket, secret):
        self.url: str = socket
        self.secret: str = secret
        self.headers: Dict = {"Authorization": f"token {secret}"}
        self.jpy_sessions: Dict = dict()

    def get(self, path="api/contents"):
        return requests.get(self.url + path, headers=self.headers).json()

    def list_running_jpy_sessions(self):
        sessions = list()
        for jpy_sess in self.get("api/sessions"):
            self.jpy_sessions[jpy_sess["id"]] = jpy_sess
            sessions.append(jpy_sess["id"])
        return sessions
