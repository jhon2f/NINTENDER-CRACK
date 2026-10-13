# crack_final.py — NINTENDER premium crack (portable, interactive, hardened)
# language: Python 3.10+, deps: frida, cryptography (emulator only)
#
# Everything lives in THIS file's folder: nintender.exe, emulator.py,
# pin_patch.json, server.crt, server.key. The one-click .bat runs this.
#
# Hardened: the license server binds a DYNAMIC free port (never 443), and a
# Frida connect() hook redirects the checker's :443 connection to that port.
# So a busy port 443, no hosts entry, IPv4/IPv6 — it self-adjusts and just works.
#
# Key: NINTENDER-premium-86400-051b6164-7f984a643a8df3b8

import subprocess, threading, time, sys, io, frida, json, os, socket as _socket

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DIR = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(DIR, "nintender.exe")
KEY = "NINTENDER-premium-86400-051b6164-7f984a643a8df3b8"

if not os.path.exists(EXE):
    print(f"[!] nintender.exe not found next to this script:\n    {EXE}")
    print("[!] Put nintender.exe in the same folder and re-run.")
    sys.exit(1)

cfg = json.load(open(os.path.join(DIR, "pin_patch.json")))
MY = cfg["my_expected"]; REAL = cfg["real_expected"]

def free_port():
    s = _socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()

dev = frida.get_local_device()

# 0. clear any stale checker/emulator processes from previous runs
for pr in dev.enumerate_processes():
    if 'nintender' in pr.name.lower():
        try: os.kill(pr.pid, 9)
        except Exception: pass
time.sleep(0.5)
existing = set(pr.pid for pr in dev.enumerate_processes())  # snapshot AFTER cleanup

# 1. dynamic free port + emulator (forged license server)
EMU_PORT = free_port()
print(f"[*] license server on 127.0.0.1:{EMU_PORT} (auto-picked free port)")
emu = subprocess.Popen([sys.executable, os.path.join(DIR, "emulator.py"), str(EMU_PORT)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)

# 2. launch checker in the SAME console (single window)
print(f"\n enter any license you want to bypass")
print(f" (for example: {KEY})\n")
p = subprocess.Popen([EXE])   # inherit console -> one window
print(f"[*] checker PID {p.pid} — waiting for the child process to spawn...")

# 3. wait for the child (spawned after the key is entered)
child_pid = None
for i in range(2000):   # up to ~100s
    for pr in dev.enumerate_processes():
        if 'nintender' in pr.name.lower() and pr.pid != p.pid and pr.pid not in existing:
            child_pid = pr.pid; break
    if child_pid: break
    time.sleep(0.05)

if not child_pid:
    print("[!] child process never appeared. Did you paste the key?")
    sys.exit(1)
print(f"[+] child {child_pid}")

# 4. attach + arm everything (pin patch, port redirect, banner)
JS = r"""
var MY="<MY>",REAL="<REAL>";
function h2b(h){var b=[];for(var i=0;i<h.length;i+=2)b.push(parseInt(h.substr(i,2),16));return b;}
var mB=h2b(MY),rB=h2b(REAL);
function L(i){send({type:'n',info:i});}
function eq(a,w){try{var u=new Uint8Array(a.readByteArray(32));for(var i=0;i<32;i++)if(u[i]!==w[i])return false;return true;}catch(e){return false;}}
function chk(md){if(!md||md.isNull())return;if(eq(md,mB)){md.writeByteArray(rB);}}
var pinArmed=false;
function arm(){if(pinArmed)return true;var lc=null;try{lc=Process.getModuleByName('libcrypto-3.dll');}catch(e){}if(!lc)return false;
var f=lc.findExportByName('HMAC_Final');if(f)Interceptor.attach(f,{onEnter:function(a){this.md=a[1];},onLeave:function(r){chk(this.md);}});
var h=lc.findExportByName('HMAC');if(h)Interceptor.attach(h,{onEnter:function(a){this.md=this.context.sp.add(0x30).readPointer();},onLeave:function(r){chk(this.md);}});
pinArmed=true;L('pin patch armed');return true;}

// resolve the license hostname -> 127.0.0.1 (account-check hosts are left alone)
var dnsArmed=false;
function dns(){if(dnsArmed)return true;var ws=null;try{ws=Process.getModuleByName('ws2_32.dll');}catch(e){}if(!ws)return false;
var gai=ws.findExportByName('getaddrinfo');if(!gai)return false;
var LOOPBACK=Memory.allocUtf8String('127.0.0.1');
Interceptor.attach(gai,{onEnter:function(args){
  var node=args[0]; if(node.isNull())return;
  try{ var s=node.readUtf8String(); if(s && s.indexOf('nintender-production')!==-1){ args[0]=LOOPBACK; } }catch(e){}
}});
dnsArmed=true;L('dns redirect armed (license host only)');return true;}

// redirect ONLY 127.0.0.1:443 (the license server) to our free port — never touch
// the Nintendo/Epic/Fortnite account-check connections
var connArmed=false;
function connect(port){if(connArmed)return true;var ws=null;try{ws=Process.getModuleByName('ws2_32.dll');}catch(e){}if(!ws)return false;
var c=ws.findExportByName('connect');if(!c)return false;
var portBE=((port&0xff)<<8)|((port>>8)&0xff);
Interceptor.attach(c,{onEnter:function(args){
  var sa=args[1]; if(sa.isNull())return;
  try{
    var fam=sa.readU16();
    if(fam===2){
      var p=sa.add(2).readU16(); var ph=((p&0xff)<<8)|((p>>8)&0xff);
      var addr=sa.add(4).readU32();   // 0x0100007f == 127.0.0.1
      if(ph===443 && addr===0x0100007f){ sa.add(2).writeU16(portBE); }
    } else if(fam===23){
      var p6=sa.add(2).readU16(); var ph6=((p6&0xff)<<8)|((p6>>8)&0xff);
      var isLoop=true; for(var i=0;i<15;i++){ if(sa.add(8+i).readU8()!==0){isLoop=false;break;} } if(sa.add(23).readU8()!==1)isLoop=false;
      if(ph6===443 && isLoop){ sa.add(2).writeU16(portBE); }
    }
  }catch(e){}
}});
connArmed=true;L('connect redirect armed (127.0.0.1:443 only)');return true;}

// banner credit (replaces "------NINTENDER------")
var CRED = "NINTENDER CRACKED\r\ncracked by sassy\r\ndiscord: sassymemelol\r\ntelegram: t.me/leakitall\r\nwant a better checker? buy https://fnfucker.lol";
var PAT  = "------NINTENDER------";
var BUFS = [];
var banArmed=false;
function rewrite(args, wide){
  var buf = args[1]; var n = args[2].toInt32();
  if (buf.isNull() || n <= 0 || n > 8192) return;
  try {
    var s = '';
    if (wide) { var raw = new Uint8Array(buf.readByteArray(n*2)); for (var k=0;k<n;k++) s += String.fromCharCode(raw[2*k]); }
    else { var raw2 = new Uint8Array(buf.readByteArray(n)); for (var k=0;k<n;k++) s += String.fromCharCode(raw2[k]); }
    var idx = s.indexOf(PAT);
    if (idx < 0) return;
    var news = s.substring(0, idx) + CRED + s.substring(idx + PAT.length);
    if (wide) {
      var wb=[]; for (var c=0;c<news.length;c++){ wb.push(news.charCodeAt(c)&0xff); wb.push(0); }
      var nb=Memory.alloc(wb.length); nb.writeByteArray(wb); BUFS.push(nb); args[1]=nb; args[2]=ptr(news.length);
    } else {
      var nb2=Memory.allocUtf8String(news); BUFS.push(nb2); args[1]=nb2; args[2]=ptr(news.length);
    }
  } catch(e){}
}
function banner(){if(banArmed)return true;var k=null;try{k=Process.getModuleByName('kernel32.dll');}catch(e){}if(!k)return false;
var wf=k.findExportByName('WriteFile'); if(wf)Interceptor.attach(wf,{onEnter:function(a){rewrite(a,false);}});
var wa=null;try{wa=k.findExportByName('WriteConsoleA');}catch(e){} if(wa)Interceptor.attach(wa,{onEnter:function(a){rewrite(a,false);}});
var ww=null;try{ww=k.findExportByName('WriteConsoleW');}catch(e){} if(ww)Interceptor.attach(ww,{onEnter:function(a){rewrite(a,true);}});
banArmed=true;L('banner hook armed');return true;}

rpc.exports={arm:arm,dns:dns,connect:connect,banner:banner};
""".replace("<MY>",MY).replace("<REAL>",REAL).replace("<PORT>", str(EMU_PORT))

ses = dev.attach(child_pid)
sc = ses.create_script(JS)
def onm(msg, data):
    if msg.get("type") == "send": print("[frida]", msg["payload"]["info"], flush=True)
    elif msg.get("type") == "error": print("JSERR", (msg.get("stack") or msg.get("description"))[:200], flush=True)
sc.on("message", onm)
sc.load()

armed = False
for i in range(2000):   # keep re-trying while modules load
    try:
        if not armed and sc.exports.arm():
            armed = True
    except Exception: pass
    try: sc.exports.dns()
    except Exception: pass
    try: sc.exports.connect(EMU_PORT)
    except Exception: pass
    try: sc.exports.banner()
    except Exception: pass
    if armed:
        break
    time.sleep(0.03)

if not armed:
    print("[!] pin patch could not arm (libcrypto not detected). Re-run.")

print("[*] crack active. Type your key above, then use the checker. Close it to end.")
try:
    while True:
        # keep everything alive until the checker (child) exits
        if not any(pr.pid == child_pid for pr in dev.enumerate_processes()):
            break
        time.sleep(1)
finally:
    try: ses.detach()
    except Exception: pass
    try: emu.terminate()
    except Exception: pass
print("done")
