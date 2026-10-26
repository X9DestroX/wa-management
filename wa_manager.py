import json, os, secrets, sqlite3, hashlib, threading, webbrowser, socket, time, shutil, ipaddress, urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

APP_NAME='W-A Systeme de Gestion'; DEFAULT_PORT=8765; DISCOVERY_PORT=8766; DISCOVERY_MAGIC='WA_MANAGER_DISCOVERY_V1'; DISCOVERY_INTERVAL=1.0; RUNTIME_ROLE='client'; RUNTIME_SERVER=''; RUNTIME_PORT=DEFAULT_PORT
DATA_DIR=os.path.join(os.path.expanduser('~'),'WA_Manager_System'); DB_PATH=os.path.join(DATA_DIR,'wa_manager.db'); CONFIG_PATH=os.path.join(DATA_DIR,'config.json'); BACKUP_DIR=os.path.join(DATA_DIR,'backups'); UI_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)),'ui.html')
os.makedirs(DATA_DIR,exist_ok=True); os.makedirs(BACKUP_DIR,exist_ok=True)
def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def hash_password(p,salt=None): salt=salt or secrets.token_hex(16); return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),120000).hex()
def verify_password(p,stored):
    try: salt,h=stored.split(':',1); return secrets.compare_digest(hash_password(p,salt).split(':',1)[1],h)
    except: return False
def db(): c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row; return c
def init_db():
    c=db()
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,full_name TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS deposits(id INTEGER PRIMARY KEY AUTOINCREMENT,amount REAL NOT NULL,department TEXT,reference TEXT,deposited_by TEXT,notes TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT,device_type TEXT NOT NULL,device_name TEXT,client_name TEXT,mobile TEXT,address TEXT,setup_by TEXT,amount REAL NOT NULL DEFAULT 0,subscription REAL NOT NULL DEFAULT 0,subscription_done INTEGER NOT NULL DEFAULT 0,expenses REAL NOT NULL DEFAULT 0,sold_at TEXT NOT NULL,notes TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT,action TEXT,details TEXT,created_at TEXT NOT NULL);""")
    # Add v1.1 calculation fields to existing installations without destroying data.
    cols={r['name'] for r in c.execute('PRAGMA table_info(sales)').fetchall()}
    migrations={
        'device_price':'REAL NOT NULL DEFAULT 0',
        'setup_price':'REAL NOT NULL DEFAULT 0',
        'sim_cost':'REAL NOT NULL DEFAULT 0',
        'activation_cost':'REAL NOT NULL DEFAULT 0',
        'benefit':'REAL NOT NULL DEFAULT 0',
        'next_month_activation':'REAL NOT NULL DEFAULT 0',
        "device_phone":"TEXT NOT NULL DEFAULT ''",
        "sim_number":"TEXT NOT NULL DEFAULT ''",
        "gps_type":"TEXT NOT NULL DEFAULT ''",
        'subscription_months':'INTEGER NOT NULL DEFAULT 1',
        'actual_subscription_monthly':'REAL NOT NULL DEFAULT 2000',
        'billed_subscription_monthly':'REAL NOT NULL DEFAULT 3000',
        'total_amount':'REAL NOT NULL DEFAULT 0'
    }
    for name,definition in migrations.items():
        if name not in cols:
            c.execute(f'ALTER TABLE sales ADD COLUMN {name} {definition}')
    # Backfill total_amount for existing records without changing their base amount.
    c.execute("UPDATE sales SET total_amount=CASE WHEN UPPER(device_type)='GPS' THEN amount + COALESCE(sim_cost,3000) + COALESCE(subscription,0) ELSE amount END WHERE total_amount=0")
    if c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']==0:
        c.execute('INSERT INTO users(username,password,role,full_name,created_at) VALUES(?,?,?,?,?)',('admin',hash_password('admin123'),'Administrateur','Administrateur',now()))
        c.execute('INSERT INTO users(username,password,role,full_name,created_at) VALUES(?,?,?,?,?)',('hr',hash_password('hr123'),'RH','Utilisateur RH',now()))
    # Migrate role labels from previous English versions to the French roles.
    c.execute("UPDATE users SET role='Administrateur' WHERE role='Manager' AND username='admin'")
    c.execute("UPDATE users SET role='Gestionnaire' WHERE role='Manager'")
    c.execute("UPDATE users SET role='RH' WHERE role='HR'")
    c.commit(); c.close()


def num(value):
    try: return float(value or 0)
    except (TypeError, ValueError): return 0.0


def calculate_sale(d):
    """GPS pricing: SIM + activation is 3,000 FCFA and already includes month 1.
    ``subscription_months`` is the number of ADDITIONAL months paid.
    Total subscription = additional months × 3,000 FCFA.
    Total to pay = base amount + 3,000 FCFA + total additional subscription.
    """
    typ=str(d.get('device_type','GPS')).strip() or 'GPS'
    months=max(0, int(num(d.get('subscription_months')) or 0))
    base=num(d.get('amount'))
    sim_activation=3000.0 if typ.upper()=='GPS' else num(d.get('sim_cost'))
    billed_monthly=3000.0 if typ.upper()=='GPS' else num(d.get('billed_subscription_monthly'))
    subscription=billed_monthly * months if typ.upper()=='GPS' else num(d.get('subscription'))
    total_amount=base + sim_activation + subscription if typ.upper()=='GPS' else base
    return {'device_price':0.0,'setup_price':0.0,'sim_cost':sim_activation,
            'activation_cost':sim_activation,'subscription':subscription,
            'subscription_months':months,'actual_subscription_monthly':0.0,
            'billed_subscription_monthly':billed_monthly,'benefit':0.0,
            'next_month_activation':0.0,'gross_total':base,'total_amount':total_amount}


def backup_database():
    """Create a consistent SQLite backup on the server at startup and daily."""
    if not os.path.exists(DB_PATH):
        return None
    stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    dest=os.path.join(BACKUP_DIR, f'wa_manager_{stamp}.db')
    try:
        src=sqlite3.connect(DB_PATH, timeout=30)
        out=sqlite3.connect(dest)
        with out:
            src.backup(out)
        out.close(); src.close()
        # Keep the latest 14 backups.
        files=sorted([os.path.join(BACKUP_DIR,f) for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], key=os.path.getmtime, reverse=True)
        for old in files[14:]:
            try: os.remove(old)
            except OSError: pass
        return dest
    except Exception:
        try:
            if os.path.exists(dest): os.remove(dest)
        except OSError: pass
        return None


def start_backup_scheduler():
    def loop():
        last_day=None
        while True:
            day=datetime.now().strftime('%Y-%m-%d')
            if day != last_day:
                backup_database(); last_day=day
            time.sleep(60)
    threading.Thread(target=loop,daemon=True).start()


def local_ip():
    # Resolve a usable private LAN address without requiring Internet access.
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('10.255.255.255',1)); ip=s.getsockname()[0]; s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass
    try:
        candidates=socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in candidates:
            if ip and not ip.startswith('127.'):
                return ip
    except Exception:
        pass
    return '127.0.0.1'


def discover_server(timeout=2.5):
    """Find a W-A Systeme de Gestion server on the local subnet using UDP broadcast."""
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    sock.settimeout(0.35)
    try:
        payload=json.dumps({'magic':DISCOVERY_MAGIC,'port':DEFAULT_PORT,'request':'discover'}).encode()
        sock.sendto(payload,('<broadcast>',DISCOVERY_PORT))
        deadline=time.time()+timeout
        candidates=[]
        while time.time()<deadline:
            try:
                raw,addr=sock.recvfrom(2048); data=json.loads(raw.decode())
                if data.get('magic')==DISCOVERY_MAGIC and data.get('role')=='server':
                    candidates.append((addr[0],int(data.get('port',DEFAULT_PORT))))
            except socket.timeout: continue
            except Exception: continue
        return candidates[0] if candidates else None
    finally: sock.close()


def discovery_responder(port):
    def loop():
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try: sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        except OSError: pass
        try: sock.bind(('',DISCOVERY_PORT))
        except OSError: return
        while True:
            try:
                raw,addr=sock.recvfrom(2048); data=json.loads(raw.decode())
                if data.get('magic')==DISCOVERY_MAGIC and data.get('request')=='discover':
                    response=json.dumps({'magic':DISCOVERY_MAGIC,'role':'server','port':port,'name':APP_NAME,'host':socket.gethostname()}).encode()
                    sock.sendto(response,(addr[0],DISCOVERY_PORT))
            except Exception:
                continue
    threading.Thread(target=loop,daemon=True).start()


def save_cfg(server,port,mode='auto'):
    with open(CONFIG_PATH,'w',encoding='utf-8') as f:
        json.dump({'server':server,'port':port,'server_mode': mode=='server','network_mode':mode},f,indent=2)

LAN_ACCESS_PATH=os.path.join(DATA_DIR,'lan_access.json')

def load_lan_access():
    default={'enabled':False,'max_clients':3,'allowed_ips':[]}
    try:
        with open(LAN_ACCESS_PATH,encoding='utf-8') as f:
            data=json.load(f)
        if not isinstance(data,dict): return default
        return {'enabled':bool(data.get('enabled',False)),'max_clients':max(1,min(3,int(data.get('max_clients',3) or 3))),'allowed_ips':[str(x).strip() for x in data.get('allowed_ips',[]) if str(x).strip()]}
    except Exception: return default

def client_ip_allowed(ip):
    access=load_lan_access()
    if not access['enabled']: return True
    if ip in ('127.0.0.1','::1','localhost'): return True
    return ip in access['allowed_ips']

class API(BaseHTTPRequestHandler):
    sessions={}
    def log_message(self,*a): pass
    def cors(self): self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Access-Control-Allow-Methods','GET,POST,DELETE,OPTIONS')
    def send_json(self,data,status=200):
        raw=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.cors(); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def body(self): n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def auth(self): return self.sessions.get(self.headers.get('Authorization','').replace('Bearer ',''))
    def network_allowed(self):
        if client_ip_allowed(self.client_address[0]): return True
        self.send_json({'error':'Cet ordinateur n’est pas autorisé à accéder à W-A Systeme de Gestion.'},403); return False
    def do_OPTIONS(self):
        if not self.network_allowed(): return
        self.send_response(204); self.cors(); self.end_headers()
    def do_GET(self):
        if not self.network_allowed(): return
        p=urlparse(self.path).path
        if p in ('/','/ui.html'):
            raw=open(UI_PATH,'rb').read(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p=='/api/health': return self.send_json({'ok':True,'app':APP_NAME})
        u=self.auth()
        if not u:return self.send_json({'error':'Non autorisé'},401)
        c=db()
        try:
            if p=='/api/network':
                access=load_lan_access(); return self.send_json({'role':RUNTIME_ROLE,'server':RUNTIME_SERVER or '127.0.0.1','port':RUNTIME_PORT,'hostname':socket.gethostname(),'local_ip':local_ip(),'online':True,'access_enabled':access['enabled'],'max_clients':access['max_clients']})
            if p=='/api/dashboard':
                date=parse_qs(urlparse(self.path).query).get('date',[datetime.now().strftime('%Y-%m-%d')])[0]
                dep=c.execute('SELECT COALESCE(SUM(amount),0)v FROM deposits WHERE date(created_at)=?',(date,)).fetchone()['v']; rev=c.execute('SELECT COALESCE(SUM(total_amount),0)v FROM sales WHERE date(sold_at)=?',(date,)).fetchone()['v']; sub=c.execute('SELECT COALESCE(SUM(subscription),0)v FROM sales WHERE date(sold_at)=?',(date,)).fetchone()['v']; exp=c.execute('SELECT COALESCE(SUM(expenses),0)v FROM sales WHERE date(sold_at)=?',(date,)).fetchone()['v']; gps=c.execute("SELECT COUNT(*)v FROM sales WHERE device_type='GPS' AND date(sold_at)=?",(date,)).fetchone()['v']; star=c.execute("SELECT COUNT(*)v FROM sales WHERE device_type='Starlink' AND date(sold_at)=?",(date,)).fetchone()['v']; recent=[dict(x) for x in c.execute('SELECT * FROM sales WHERE date(sold_at)=? ORDER BY id DESC LIMIT 8',(date,))]; rd=[dict(x) for x in c.execute('SELECT * FROM deposits WHERE date(created_at)=? ORDER BY id DESC LIMIT 8',(date,))]; return self.send_json({'deposits':dep,'revenue':rev,'subscriptions':sub,'expenses':exp,'gps':gps,'starlink':star,'recent':recent,'recent_deposits':rd})
            if p=='/api/deposits':return self.send_json({'items':[dict(x) for x in c.execute('SELECT * FROM deposits ORDER BY id DESC LIMIT 200')]})
            if p=='/api/sales':return self.send_json({'items':[dict(x) for x in c.execute('SELECT * FROM sales ORDER BY id DESC LIMIT 200')]})
            if p=='/api/users':
                return self.send_json({'items':[dict(x) for x in c.execute('SELECT id,username,role,full_name,created_at FROM users ORDER BY id')]})
            return self.send_json({'error':'Introuvable'},404)
        finally:c.close()
    def do_POST(self):
        if not self.network_allowed(): return
        p=urlparse(self.path).path; d=self.body()
        if p=='/api/login':
            c=db(); u=c.execute('SELECT * FROM users WHERE username=?',(d.get('username',''),)).fetchone(); c.close()
            if not u or not verify_password(d.get('password',''),u['password']):return self.send_json({'error':'Nom d’utilisateur ou mot de passe incorrect'},401)
            tok=secrets.token_urlsafe(32); self.sessions[tok]={'id':u['id'],'username':u['username'],'role':u['role'],'full_name':u['full_name']}; return self.send_json({'token':tok,'user':self.sessions[tok]})
        u=self.auth()
        if not u:return self.send_json({'error':'Non autorisé'},401)
        c=db(); cur=c.cursor()
        try:
            if p=='/api/deposits':cur.execute('INSERT INTO deposits(amount,department,reference,deposited_by,notes,created_at)VALUES(?,?,?,?,?,?)',(float(d.get('amount',0)),d.get('department','Finance'),d.get('reference',''),d.get('deposited_by','') or u['full_name'] or u['username'],d.get('notes',''),d.get('created_at') or now()))
            elif p.startswith('/api/deposits/') and p.endswith('/edit'):
                uid=p.split('/')[-2]
                if not uid.isdigit(): return self.send_json({'error':'Identifiant du dépôt invalide'},400)
                target=cur.execute('SELECT * FROM deposits WHERE id=?',(int(uid),)).fetchone()
                if not target:return self.send_json({'error':'Dépôt introuvable'},404)
                cur.execute('UPDATE deposits SET amount=?,department=?,reference=?,deposited_by=?,notes=?,created_at=? WHERE id=?',(
                    float(d.get('amount',target['amount'])),d.get('department',target['department'] or 'Finance'),d.get('reference',target['reference'] or ''),
                    d.get('deposited_by',target['deposited_by'] or ''),d.get('notes',target['notes'] or ''),d.get('created_at',target['created_at']),int(uid)))
            elif p=='/api/sales':
                calc=calculate_sale(d)
                # Amount is the actual final amount collected, calculated from the commercial breakdown.
                amount=calc['total_amount']
                cur.execute('''INSERT INTO sales(device_type,device_name,client_name,mobile,device_phone,sim_number,gps_type,address,setup_by,amount,subscription,subscription_done,expenses,sold_at,notes,device_price,setup_price,sim_cost,activation_cost,benefit,next_month_activation,subscription_months,actual_subscription_monthly,billed_subscription_monthly,total_amount)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (d.get('device_type'),d.get('device_name',''),d.get('client_name',''),d.get('mobile',''),d.get('sim_number',''),d.get('sim_number',''),d.get('gps_type',''),d.get('address',''),d.get('setup_by',''),
                     num(d.get('amount')),calc['subscription'],1 if d.get('subscription_done') else 0,0,d.get('sold_at') or now(),d.get('notes',''),
                     0,0,calc['sim_cost'],calc['activation_cost'],0,0,calc['subscription_months'],0,calc['billed_subscription_monthly'],calc['total_amount']))
            elif p.startswith('/api/sales/') and p.endswith('/edit'):
                uid=p.split('/')[-2]
                if not uid.isdigit(): return self.send_json({'error':'Identifiant de vente invalide'},400)
                target=cur.execute('SELECT * FROM sales WHERE id=?',(int(uid),)).fetchone()
                if not target:return self.send_json({'error':'Vente introuvable'},404)
                # Preserve the hidden commercial parameters while allowing corrections to all visible sale fields.
                calc_input=dict(target)
                calc_input.update(d)
                calc=calculate_sale(calc_input)
                final_amount = float(d['amount']) if str(d.get('amount','')).strip() else target['amount']
                final_subscription = calc['subscription']
                cur.execute('''UPDATE sales SET device_type=?,device_name=?,client_name=?,mobile=?,device_phone=?,sim_number=?,gps_type=?,address=?,setup_by=?,amount=?,subscription=?,subscription_done=?,expenses=?,sold_at=?,notes=?,device_price=?,setup_price=?,sim_cost=?,activation_cost=?,benefit=?,next_month_activation=?,subscription_months=?,actual_subscription_monthly=?,billed_subscription_monthly=?,total_amount=? WHERE id=?''',(
                    d.get('device_type',target['device_type']),d.get('device_name',target['device_name'] or ''),d.get('client_name',target['client_name'] or ''),
                    d.get('mobile',target['mobile'] or ''),d.get('device_phone',target['device_phone'] or ''),d.get('sim_number',target['sim_number'] if 'sim_number' in target.keys() else ''),d.get('gps_type',target['gps_type'] if 'gps_type' in target.keys() else ''),d.get('address',target['address'] or ''),
                    d.get('setup_by',target['setup_by'] or ''),final_amount,final_subscription,1 if d.get('subscription_done') else 0,
                    0,d.get('sold_at') or target['sold_at'],d.get('notes',target['notes'] or ''),0,0,
                    calc['sim_cost'],calc['activation_cost'],0,0,calc['subscription_months'],0,
                    calc['billed_subscription_monthly'],calc['total_amount'],int(uid)))
            elif p=='/api/users':
                if u['role']!='Administrateur':return self.send_json({'error':'Accès réservé à l’administrateur'},403)
                role=str(d.get('role','')).strip()
                if role not in ('RH','Gestionnaire','Administrateur'):return self.send_json({'error':'Rôle invalide'},400)
                if not str(d.get('username','')).strip() or not str(d.get('password','')):return self.send_json({'error':'Nom d’utilisateur et mot de passe obligatoires'},400)
                cur.execute('INSERT INTO users(username,password,role,full_name,created_at)VALUES(?,?,?,?,?)',(d['username'].strip(),hash_password(d['password']),role,d.get('full_name','').strip(),now()))
            elif p.startswith('/api/users/') and p.endswith('/edit'):
                if u['role']!='Administrateur':
                    return self.send_json({'error':'Accès réservé à l’administrateur'},403)
                uid=p.split('/')[-2]
                if not uid.isdigit(): return self.send_json({'error':'Identifiant utilisateur invalide'},400)
                target=cur.execute('SELECT * FROM users WHERE id=?',(int(uid),)).fetchone()
                if not target:return self.send_json({'error':'Utilisateur introuvable'},404)
                username=str(d.get('username',target['username'])).strip()
                full_name=str(d.get('full_name',target['full_name'] or '')).strip()
                role=str(d.get('role',target['role'])).strip()
                if not username:return self.send_json({'error':'Le nom d’utilisateur est obligatoire'},400)
                if role not in ('RH','Gestionnaire','Administrateur'):return self.send_json({'error':'Rôle invalide'},400)
                if d.get('password',''):
                    cur.execute('UPDATE users SET username=?,password=?,role=?,full_name=? WHERE id=?',(username,hash_password(d['password']),role,full_name,int(uid)))
                else:
                    cur.execute('UPDATE users SET username=?,role=?,full_name=? WHERE id=?',(username,role,full_name,int(uid)))
            else:return self.send_json({'error':'Introuvable'},404)
            cur.execute('INSERT INTO audit(username,action,details,created_at)VALUES(?,?,?,?)',(u['username'],p,json.dumps(d),now())); c.commit(); return self.send_json({'ok':True})
        except sqlite3.IntegrityError:return self.send_json({'error':'Ce nom d’utilisateur existe déjà'},400)
        except Exception as e:c.rollback(); return self.send_json({'error':str(e)},400)
        finally:c.close()
    def do_DELETE(self):
        if not self.network_allowed(): return
        p=urlparse(self.path).path; u=self.auth()
        if not u:return self.send_json({'error':'Non autorisé'},401)
        c=db()
        try:
            if p.startswith('/api/users/') and p.rsplit('/',1)[-1].isdigit():
                if u['role']!='Administrateur':return self.send_json({'error':'Accès réservé à l’administrateur'},403)
                uid=int(p.rsplit('/',1)[-1])
                if uid==u['id']:return self.send_json({'error':'Vous ne pouvez pas supprimer votre propre compte'},400)
                target=c.execute('SELECT id,role FROM users WHERE id=?',(uid,)).fetchone()
                if not target:return self.send_json({'error':'Utilisateur introuvable'},404)
                if target['role']=='Administrateur' and c.execute("SELECT COUNT(*) n FROM users WHERE role='Administrateur'").fetchone()['n']<=1:
                    return self.send_json({'error':'Impossible de supprimer le dernier administrateur'},400)
                c.execute('DELETE FROM users WHERE id=?',(uid,))
            elif p.startswith('/api/sales/') and p.rsplit('/',1)[-1].isdigit():
                c.execute('DELETE FROM sales WHERE id=?',(int(p.rsplit('/',1)[-1]),))
            elif p.startswith('/api/deposits/') and p.rsplit('/',1)[-1].isdigit():
                c.execute('DELETE FROM deposits WHERE id=?',(int(p.rsplit('/',1)[-1]),))
            else:return self.send_json({'error':'Introuvable'},404)
            c.commit(); return self.send_json({'ok':True})
        finally:c.close()

def cfg():
    try:
        c=json.load(open(CONFIG_PATH,encoding='utf-8'))
        c.setdefault('port',DEFAULT_PORT)
        changed=False
        # Old builds stored server_mode=True without an explicit network_mode.
        if 'network_mode' not in c:
            c['network_mode']='auto'; c['server_mode']=False; c['server']=''; changed=True
        # Repair the common copied-config problem: a local server config
        # (127.0.0.1 + server_mode=true) copied to every laptop. In AUTO mode
        # the application must discover the existing LAN server instead of
        # forcing every laptop to become a server.
        elif str(c.get('network_mode','')).lower()=='server' and str(c.get('server','')).strip() in ('','127.0.0.1','localhost') and bool(c.get('server_mode')):
            c['network_mode']='auto'; c['server_mode']=False; c['server']=''; changed=True
        if changed:
            try:
                with open(CONFIG_PATH,'w',encoding='utf-8') as f: json.dump(c,f,indent=2)
            except Exception: pass
        return c
    except Exception:
        return {'server':'','port':DEFAULT_PORT,'server_mode':False,'network_mode':'auto'}

def start_server(port):
    init_db(); backup_database(); start_backup_scheduler(); discovery_responder(port)
    s=ThreadingHTTPServer(('0.0.0.0',port),API); threading.Thread(target=s.serve_forever,daemon=True).start(); return s

def server_is_alive(host,port,timeout=0.8):
    try:
        with socket.create_connection((host,port),timeout=timeout): return True
    except OSError: return False

def main():
    global RUNTIME_ROLE, RUNTIME_SERVER, RUNTIME_PORT
    c=cfg(); port=int(c.get('port',DEFAULT_PORT)); mode=str(c.get('network_mode','auto')).lower()
    configured_server=str(c.get('server','')).strip()
    server_mode=False; server_host=''

    if mode=='server' or bool(c.get('server_mode')):
        server_mode=True
    elif mode=='client':
        if configured_server and server_is_alive(configured_server,port):
            server_host=configured_server
        else:
            # If the configured server is unavailable, try discovery before failing over.
            found=discover_server()
            if found: server_host,port=found
            else: server_host=configured_server
    else:
        # Auto mode: find an existing server first. If none exists, wait a short randomized
        # period so two PCs started together don't both immediately become servers.
        found=discover_server()
        if found:
            server_host,port=found; save_cfg(server_host,port,'client')
        else:
            time.sleep(0.35 + (secrets.randbelow(1500)/1000.0))
            found=discover_server(timeout=1.0)
            if found:
                server_host,port=found; save_cfg(server_host,port,'client')
            else:
                server_mode=True; save_cfg(local_ip(),port,'server')

    if server_mode:
        start_server(port); RUNTIME_ROLE='server'; RUNTIME_SERVER=local_ip(); RUNTIME_PORT=port; url=f'http://127.0.0.1:{port}/'
    else:
        if not server_host:
            # Client mode should never silently create a second database.
            # If the configured server cannot be reached, retry discovery.
            found=discover_server(timeout=2.5)
            if found: server_host,port=found
        if not server_host:
            raise SystemExit('W-A Systeme de Gestion Server was not found on the LAN. Start the main computer first.')
        RUNTIME_ROLE='client'; RUNTIME_SERVER=server_host; RUNTIME_PORT=port; url=f'http://{server_host}:{port}/'

    try:
        import webview
        webview.create_window(APP_NAME,url,width=1500,height=900,min_size=(1100,700),resizable=True)
        webview.start()
    except ImportError:
        print('pywebview is not installed. Run: pip install -r requirements.txt'); webbrowser.open(url); input('Press Enter to exit...')
if __name__=='__main__':main()
