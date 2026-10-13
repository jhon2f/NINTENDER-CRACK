# NINTENDER CRACK

One-click crack for the NINTENDER premium Nintendo account checker. Bypasses the license + cert pin so it runs full `premium` with a lifetime license — account checks still hit the real Nintendo/Epic servers.

## Usage

1. Download / clone this repo.
2. Double-click **`NINTENDER-CRACK.bat`**.
3. It auto-installs Python + `frida` + `cryptography` if missing, then launches.
4. When it says `enter any license you want to bypass`, paste any key (or the example) and press Enter.
5. Type `1` for checker, drag in your combo file, and go.

No admin, no port conflicts, one window. First run needs internet for the two pip packages; after that it's instant.

## How it works

The target is `nintender.exe` — a Themida-wrapped bootloader that spawns an **unprotected child** (`nintendo.dll`, a Nuitka build + `python312.dll`). That child is where everything is patched at runtime with Frida.

Three gates are bypassed:

1. **License server** — the checker phones `nintender-production.up.railway.app/verify` with an AES-GCM-encrypted payload. The key was recovered (`a82e1b19...`), and the server accepts any key, so a local `emulator.py` forges an `ok:true` / `tier:premium` / ~100-year-expiry response instead of contacting it.

2. **Cert pin** — the checker verifies the license server's cert with `HMAC-SHA256(pin_key, SHA256(cert_der))`. By hooking `HMAC_Final` in `libcrypto`, the computed pin for our self-signed cert is rewritten to the real cert's expected pin, so the check passes.

3. **Routing** — `getaddrinfo` is hooked to resolve only the license hostname to `127.0.0.1`, and `connect()` is hooked to redirect `127.0.0.1:443` to the emulator's dynamic free port. **Everything else (Nintendo / Epic / Fortnite account checks) is left untouched**, so real hits flow exactly like the legit build.

A `WriteFile`/`WriteConsoleA`/`WriteConsoleW` hook swaps the `------NINTENDER------` banner for the credit at the output layer.

## Files

| File | Purpose |
|---|---|
| `NINTENDER-CRACK.bat` | One-click launcher (setup + run) |
| `crack_final.py` | Frida patcher (pin, routing, banner) |
| `emulator.py` | Forged license server (dynamic free port) |
| `pin_patch.json` | Recovered pin key + HMAC values |
| `server.crt` / `server.key` | Self-signed cert (SAN = license host) |
| `nintender.exe` | The target binary |

## Requirements

- Windows 10/11
- Internet on first run (pip)
- Nothing else — no admin, no hosts edit
