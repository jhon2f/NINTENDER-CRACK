# emulator.py — forged NINTENDER license server (portable)
# language: Python 3.10+, dep: cryptography
# Serves a forged AES-GCM "ok:true, lifetime" license response on 127.0.0.1:443.
# Cert + log live in this file's own folder.
import socket, ssl, threading, sys, time, os, json, base64, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CERTDIR = os.path.dirname(os.path.abspath(__file__))
# port is passed by the launcher (dynamic free port); fall back to 443
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 443
LISTEN = ("127.0.0.1", PORT)
GCM_KEY = bytes.fromhex("a82e1b19aca44e864ec5f3bc9698300dea315ce294e62955aa4e6ac9b1486400")
LOGFILE = os.path.join(CERTDIR, "emulator.log")

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass

def read_http(sock, timeout=20):
    sock.settimeout(timeout)
    data = b""
    while b"\r\n\r\n" not in data:
        c = sock.recv(4096)
        if not c: return data or None
        data += c
        if len(data) > 2*1024*1024: break
    head, _, rest = data.partition(b"\r\n\r\n")
    cl = 0
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            cl = int(line.split(b":",1)[1].strip())
    body = rest
    while len(body) < cl:
        c = sock.recv(4096)
        if not c: break
        body += c
    return head + b"\r\n\r\n" + body

def forge_response():
    now = int(time.time())
    duration = 3153600000          # ~100 years -> "lifetime"
    payload = {
        "bound_at": now,
        "duration": duration,
        "expires": now + duration,
        "first_bind": False,
        "nonce": secrets.token_hex(16),
        "ok": True,
        "tier": "premium",
        "ts": now,
    }
    plain = json.dumps(payload, separators=(",", ":")).encode()
    nonce = os.urandom(12)
    ct = AESGCM(GCM_KEY).encrypt(nonce, plain, None)
    body = base64.b64encode(nonce + ct)
    return now, body

def handle(client):
    try:
        sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sctx.load_cert_chain(os.path.join(CERTDIR, "server.crt"), os.path.join(CERTDIR, "server.key"))
        tls = sctx.wrap_socket(client, server_side=True)
        req = read_http(tls)
        if not req:
            tls.close(); return
        head, _, _ = req.partition(b"\r\n\r\n")
        line0 = head.split(b"\r\n")[0].decode(errors="replace")
        log("REQ " + line0)
        now, body = forge_response()
        resp = (b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/octet-stream\r\n"
                + f"x-ts: {now}\r\n".encode()
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + body)
        tls.sendall(resp)
        log(f"forged ok:true lifetime (ts={now}, {len(body)}B body)")
        tls.close()
    except Exception as e:
        log("ERR " + repr(e))
    finally:
        try: client.close()
        except Exception: pass

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(LISTEN)
    srv.listen(50)
    log(f"emulator on {LISTEN}, forging lifetime premium")
    while True:
        c, a = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()

if __name__ == "__main__":
    main()
