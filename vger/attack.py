import uuid
import asyncio
import json
from urllib.parse import urlparse
from websockets import connect
import argparse
from vger.connection import Connection
import re


async def attack_session(
    connection, session, code, silent=False, print_out=True, get_hist=False
):
    jpy_sess = connection.jpy_sessions[session]
    code_msg_id = str(uuid.uuid1())
    code_msg = {
        "channel": "shell",
        "content": {"silent": silent, "code": code},
        "header": {"msg_id": code_msg_id, "msg_type": "execute_request"},
        "metadata": {},
        "parent_header": {},
    }

    async def recv_all(conn):
        while True:
            try:
                async with asyncio.timeout(1):
                    msg = json.loads(await conn.recv())
                    if get_hist and msg["msg_type"] == "stream":
                        connection.con.print(msg["content"]["text"])
                    if "status" not in msg["msg_type"]:
                        if print_out:
                            connection.con.print(
                                f"  type: {msg['msg_type']:16} content: {msg['content']}"
                            )
            except:
                break

    ws_base_url = urlparse(connection.url)._replace(scheme="ws").geturl()
    ws_url = (
        ws_base_url
        + f'api/kernels/{jpy_sess['kernel']['id']}/channels?session_id={jpy_sess['id']}'
    )

    async with connect(
        ws_url, extra_headers=connection.headers, close_timeout=5
    ) as conn:
        await recv_all(conn)
        if print_out:
            connection.con.print(code_msg)
        await conn.send(json.dumps(code_msg))
        return await recv_all(conn)


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
        connection.con.print("".join(result))
    connection.delete_terminal(new_term["name"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to target")
    parser.add_argument("socket", type=str, help="Target socket as http://host:port/")
    parser.add_argument("secret", type=str, help="Token or password")
    args = parser.parse_args()
    c = Connection(args.socket, args.secret)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run_ephemeral_terminal(c, "ls"))
