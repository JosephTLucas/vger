import requests
from rich.console import Console
import argparse


class Connection:
    def __init__(self, socket, secret):
        self.url = socket
        self.secret = secret
        self.headers = {"Authorization": f"token {secret}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.jpy_sessions = dict()
        self.con = Console()

    def get(self, path="api/contents"):
        return self.session.get(self.url + path).json()

    def list_running_jpy_sessions(self):
        sessions = list()
        for jpy_sess in self.get("api/sessions"):
            self.jpy_sessions[jpy_sess["id"]] = jpy_sess
            sessions.append(jpy_sess["id"])
        return sessions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to target")
    parser.add_argument("socket", type=str, help="Target socket as http://host:port/")
    parser.add_argument("secret", type=str, help="Token or password")
    args = parser.parse_args()
    c = Connection(args.socket, args.secret)
    print(c.list_running_jpy_sessions())
