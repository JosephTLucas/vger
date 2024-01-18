import requests
from rich.console import Console
import argparse
import json
import urllib.parse


class Connection:
    def __init__(self, socket, secret):
        self.url = socket
        self.secret = secret
        self.headers = {"Authorization": f"token {secret}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.jpy_sessions = dict()
        self.con = Console()
        self.jpy_terminals = dict()

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
            return {"Result": "Invalid Path"}

    def upload(self, path, data):
        return self.session.put(
            self.url + f"api/contents/{urllib.parse.quote(path)}", data=data
        ).json()

    def delete(self, path):
        return self.session.delete(
            self.url + f"api/contents/{urllib.parse.quote(path)}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to target")
    parser.add_argument("socket", type=str, help="Target socket as http://host:port/")
    parser.add_argument("secret", type=str, help="Token or password")
    parser.add_argument("path", type=str, help="list path")
    args = parser.parse_args()
    c = Connection(args.socket, args.secret)
    print(c.list_dir(args.path))
