import json

def recv_all(conn):
    while True:
        try:
            msg = json.loads(conn.recv())
            if "status" not in msg["msg_type"]:
                yield f"  type: {msg['msg_type']:16} content: {msg['content']}"
        except:
            break