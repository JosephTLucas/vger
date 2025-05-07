import requests
from rich.console import Console
import json
import urllib.parse
from typing import Dict, Optional
import rich
from datetime import datetime
from vger.auth import AuthStrategy, TokenAuthStrategy


class Connection:
    def __init__(self, socket: str = "", secret: Optional[str] = None, auth_strategy: Optional[AuthStrategy] = None):
        if auth_strategy:
            self.auth_strategy = auth_strategy
        elif secret:
            self.auth_strategy = TokenAuthStrategy(secret)
        else:
            # This case should ideally be handled by the caller ensuring either secret or auth_strategy is provided.
            # For now, to prevent immediate breakage, we can raise an error or default carefully.
            # Raising an error is cleaner for new design, but for "don't break anything", 
            # we need to see how Connection() is called with no args (e.g. in Menu)
            # Menu() calls Connection() with no args, then calls login(). login() then creates a new Connection.
            # So, we can allow this initial state, but auth_strategy must be set before use.
            self.auth_strategy = None # Will be set properly in Menu.login or by CLI

        self.raw_url = socket # Store the initial socket/url
        self.url: str = self.auth_strategy.get_target_url(socket) if self.auth_strategy else socket
        # self.secret: Optional[str] = secret # Keep for DumbConnection or if strategy needs it
        # The concept of a single 'secret' might be too simple now.
        # Let's keep it if TokenAuthStrategy is used, otherwise it's None or managed by the strategy
        self.secret: Optional[str] = secret if isinstance(self.auth_strategy, TokenAuthStrategy) else None

        self.session: requests.Session = requests.Session()
        if self.auth_strategy:
            self.session = self.auth_strategy.prepare_session(self.session, self.url)
        
        # self.headers is now primarily for WebSockets or direct use if needed.
        # For HTTP requests, the session handles headers.
        self.headers: Dict = self.auth_strategy.get_headers() if self.auth_strategy else {}

        self.jpy_sessions: Dict = dict()
        self.con: Console = Console(record=True)
        self.jpy_terminals: Dict = dict()
        # self.sessions = list() # This was ambiguously named, jpy_sessions seems to be the main one.
                               # Let's track targeted sessions if that's what it was for
        self.target_session_ids = list() # Renamed for clarity if it was for selected targets
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

    # Method to re-initialize connection details if auth strategy changes or resolves later
    def update_connection_details(self, socket_url: str, auth_strategy: AuthStrategy):
        self.auth_strategy = auth_strategy
        self.raw_url = socket_url
        self.url = self.auth_strategy.get_target_url(socket_url)
        self.secret = auth_strategy.secret if isinstance(auth_strategy, TokenAuthStrategy) else None
        self.session = requests.Session() # Reset session
        self.session = self.auth_strategy.prepare_session(self.session, self.url)
        self.headers = self.auth_strategy.get_headers()
        # Reset state that might depend on the old connection
        self.jpy_sessions = dict()
        self.jpy_terminals = dict()
        self.target = None

    def print_with_rule(self, text, category="Output", use_json=False):
        self.con.rule(f"[bold green]{category}")
        if use_json:
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
        # For post, data is usually involved, but this one seems to be parameter-less for creating terminals
        return self.session.post(self.url + path).json()

    def list_running_jpy_sessions(self):
        sessions = list()
        # Ensure self.url is valid before making a request
        if not self.url or not self.auth_strategy:
            self.print_with_rule("Connection not fully initialized. Please login.", category="Error")
            return sessions
        try:
            for jpy_sess in self.get("api/sessions"):
                self.jpy_sessions[jpy_sess["id"]] = jpy_sess
                sessions.append(jpy_sess["id"])
        except requests.exceptions.RequestException as e:
            self.print_with_rule(f"Error fetching Jupyter sessions: {e}", category="Error")
        return sessions

    def list_running_jpy_terminals(self):
        terminals = list()
        if not self.url or not self.auth_strategy: return terminals # Guard
        try:
            for jpy_term in self.get("api/terminals"):
                self.jpy_terminals[jpy_term["name"]] = jpy_term["last_activity"]
                terminals.append(jpy_term["name"])
        except requests.exceptions.RequestException as e:
            self.print_with_rule(f"Error fetching Jupyter terminals: {e}", category="Error")
        return terminals

    def create_terminal(self):
        if not self.url or not self.auth_strategy: return None # Guard
        try:
            new_term = self.post("api/terminals")
            self.jpy_terminals[new_term["name"]] = new_term["last_activity"]
            return new_term
        except requests.exceptions.RequestException as e:
            self.print_with_rule(f"Error creating terminal: {e}", category="Error")
            return None

    def delete_terminal(self, terminal):
        if not self.url or not self.auth_strategy: return # Guard
        try:
            self.session.delete(self.url + f"api/terminals/{terminal}")
        except requests.exceptions.RequestException as e:
            self.print_with_rule(f"Error deleting terminal {terminal}: {e}", category="Error")

    def list_dir(self, path):
        if not self.url or not self.auth_strategy: return {"Error": "Connection not initialized"} # Guard
        try:
            return self.get(f"api/contents/{urllib.parse.quote(path)}")
        except requests.exceptions.JSONDecodeError:
            return {"Error": "Invalid Path or Not JSON Response"}
        except requests.exceptions.RequestException as e:
            return {"Error": f"Request failed: {e}"}

    def upload(self, path, data):
        if not self.url or not self.auth_strategy: return json.dumps({"Error": "Connection not initialized"}) # Guard
        try:
            # The actual PUT request happens here using the prepared session
            response = self.session.put(
                self.url + f"api/contents/{urllib.parse.quote(path)}", data=data
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return json.dumps(
                {"Error": "There is a problem with the specified file and/or path, or server did not return JSON."}
            )
        except requests.exceptions.RequestException as e:
             return json.dumps({"Error": f"Upload failed: {e}"})

    def delete(self, path):
        if not self.url or not self.auth_strategy: return None # Guard, or an object indicating failure
        try:
            response = self.session.delete(
                self.url + f"api/contents/{urllib.parse.quote(path)}"
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.print_with_rule(f"Error deleting file {path}: {e}", category="Error")
            return None


class DumbConnection:
    """
    Pickle-serializable Connection for Python process spawning.
    Reduced functionality, primarily for websocket interactions that need headers.
    """
    def __init__(self, socket_url: str, auth_strategy: AuthStrategy):
        # DumbConnection needs a fully resolved URL and a concrete auth strategy
        self.auth_strategy = auth_strategy
        self.url: str = self.auth_strategy.get_target_url(socket_url) # Should already be resolved by caller
        self.headers: Dict = self.auth_strategy.get_headers()
        self.jpy_sessions: Dict = dict() # For attack.py stomp compatibility
        self.secret = auth_strategy.secret if isinstance(auth_strategy, TokenAuthStrategy) else None

    # This 'get' is used by attack.py's stomp to re-list sessions. It needs to be simple.
    def get(self, path="api/contents"):
        # DumbConnection makes direct requests, not using a persistent session object from the main Connection
        try:
            response = requests.get(self.url + path, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[DumbConnection] Error during GET {path}: {e}") # Simple print, no rich console
            return [] # attack.py expects an iterable for sessions
        except requests.exceptions.JSONDecodeError:
            print(f"[DumbConnection] Error decoding JSON from GET {path}")
            return []

    def list_running_jpy_sessions(self):
        sessions = list()
        api_sessions = self.get("api/sessions") # api_sessions will be empty list on error
        if isinstance(api_sessions, list): # Check if it's a list, not dict from error
            for jpy_sess in api_sessions:
                if isinstance(jpy_sess, dict) and 'id' in jpy_sess:
                    self.jpy_sessions[jpy_sess["id"]] = jpy_sess
                    sessions.append(jpy_sess["id"])
                else:
                    print(f"[DumbConnection] Unexpected session item format: {jpy_sess}")
        else:
            print(f"[DumbConnection] Unexpected response from api/sessions: {api_sessions}")
        return sessions
