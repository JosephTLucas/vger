import uuid
import asyncio
import json
from urllib.parse import urlparse
from websockets import connect

async def attack_session(connection, session, code, silent=False, print_out=True, get_hist=False):
    jpy_sess = connection.jpy_sessions[session]
    code_msg_id = str(uuid.uuid1())
    code_msg = {'channel': 'shell',
                'content': {'silent': silent, 'code': code},
                'header': {'msg_id': code_msg_id, 'msg_type':'execute_request'},
                'metadata': {},
                'parent_header':{}}
    async def recv_all(conn):
        while True:
            try:
                async with asyncio.timeout(1):
                    msg = json.loads(await conn.recv())
                    if get_hist and msg['msg_type'] == "stream":
                                connection.con.print(msg['content']['text'])
                    if "status" not in msg["msg_type"]:
                        if print_out:
                            connection.con.print(f"  type: {msg['msg_type']:16} content: {msg['content']}")  
            except:
                break

    ws_base_url = urlparse(connection.url)._replace(scheme='ws').geturl()
    ws_url = ws_base_url + f'api/kernels/{jpy_sess['kernel']['id']}/channels?session_id={jpy_sess['id']}'

    async with connect(ws_url, extra_headers=connection.headers, close_timeout=5) as conn:
        await recv_all(conn)
        if print_out:
            connection.con.print(code_msg)
        await conn.send(json.dumps(code_msg))
        return await recv_all(conn)