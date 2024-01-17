import json
import asyncio

async def recv_all(conn):
    while True:
        try:
            msgs = list()
            async with asyncio.timeout(1):
                msg = json.loads(await conn.recv())
                msgs.append(msg)
                return [f"{msg['msg_type']}: {msg['content']}" for msg in msgs]
        except:
            return ["Nothing"]