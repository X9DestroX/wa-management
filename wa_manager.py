import json, os, re, secrets, sqlite3, hashlib, threading, webbrowser, socket, time, shutil, ipaddress, urllib.request, urllib.error, base64
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode, quote

APP_NAME='W-A Systeme de Gestion'; DEFAULT_PORT=8765; DISCOVERY_PORT=8766; DISCOVERY_MAGIC='WA_MANAGER_DISCOVERY_V1'; DISCOVERY_INTERVAL=1.0; RUNTIME_ROLE='client'; RUNTIME_SERVER=''; RUNTIME_PORT=DEFAULT_PORT
DATA_DIR=os.path.join(os.path.expanduser('~'),'WA_Manager_System'); DB_PATH=os.path.join(DATA_DIR,'wa_manager.db'); CONFIG_PATH=os.path.join(DATA_DIR,'config.json'); BACKUP_DIR=os.path.join(DATA_DIR,'backups'); UI_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)),'ui.html')

os.makedirs(DATA_DIR,exist_ok=True); os.makedirs(BACKUP_DIR,exist_ok=True)
CLOUD_CONFIG_PATH=os.path.join(DATA_DIR,'cloud_config.json')

class CloudAPIError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status=status

def load_cloud_config():
    try:
        with open(CLOUD_CONFIG_PATH, encoding='utf-8-sig') as f:
            c=json.load(f)
        url=str(c.get('supabase_url','')).strip().rstrip('/')
        key=str(c.get('publishable_key','')).strip()
        enabled=bool(c.get('enabled')) and bool(url) and bool(key)
        if enabled:
            if not url.startswith('https://') or '.supabase.co' not in url:
                raise ValueError('L’URL Supabase doit commencer par https:// et se terminer par .supabase.co.')
            if key.startswith('sb_secret_') or key.startswith('sb_service_role_'):
                raise ValueError('Utilisez la clé Publishable/anon, jamais une clé Secret/service-role dans cette application.')
            # Legacy Supabase JWT-format keys can be distinguished by their payload role.
            if key.count('.') == 2:
                try:
                    part=key.split('.')[1]
                    part += '=' * ((4-len(part)%4)%4)
                    claims=json.loads(base64.urlsafe_b64decode(part.encode('ascii')).decode('utf-8'))
                    if claims.get('role') in ('service_role','supabase_admin'):
                        raise ValueError('Une clé service_role a été détectée. Supprimez-la de ce PC et utilisez la clé Publishable/anon.')
                except ValueError:
                    raise
                except Exception:
                    pass
        return {'enabled': enabled, 'supabase_url':url, 'publishable_key':key}
    except FileNotFoundError:
        return {'enabled':False}
    except Exception as e:
        return {'enabled':False,'error':str(e)}

def cloud_enabled():
    return bool(load_cloud_config().get('enabled'))

def _supabase_raw(cfg, path, method='GET', access_token=None, payload=None, prefer=None):
    url=cfg['supabase_url']+path
    headers={'apikey':cfg['publishable_key'],'Accept':'application/json','Content-Type':'application/json'}
    if access_token:
        headers['Authorization']='Bearer '+access_token
    if prefer:
        headers['Prefer']=prefer
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw=resp.read()
            if not raw: return None
            try: return json.loads(raw.decode('utf-8'))
            except Exception: return raw.decode('utf-8',errors='replace')
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8',errors='replace')
        try:
            j=json.loads(raw); msg=j.get('message') or j.get('msg') or j.get('error_description') or j.get('error') or raw
        except Exception: msg=raw or f'Erreur HTTP {e.code}'
        if e.code == 401:
            raise CloudAPIError(str(msg) or 'Session expirée.',401)
        if e.code == 403:
            raise CloudAPIError(str(msg) or 'Accès refusé.',403)
        if e.code == 404:
            raise CloudAPIError(str(msg) or 'Ressource introuvable.',404)
        if e.code == 409:
            raise CloudAPIError(str(msg) or 'Conflit de données.',409)
        raise CloudAPIError(str(msg)[:500], e.code if 400 <= e.code < 600 else 400)
    except urllib.error.URLError as e:
        raise CloudAPIError('Connexion Supabase impossible. Vérifiez Internet, l’URL du projet et votre connexion.',503)

def supabase_request(path, method='GET', session=None, payload=None, prefer=None):
    cfg=load_cloud_config()
    if not cfg.get('enabled'):
        raise CloudAPIError(cfg.get('error') or 'Configuration cloud absente. Exécutez configure_cloud.bat.',503)
    access=session.get('cloud_access_token') if session else None
    try:
        return _supabase_raw(cfg,path,method,access,payload,prefer)
    except CloudAPIError as e:
        if e.status != 401 or not session or not session.get('cloud_refresh_token') or path.startswith('/auth/v1/token?'):
            raise
        # Refresh the expired Supabase session and retry exactly once.
        refreshed=_supabase_raw(cfg,'/auth/v1/token?grant_type=refresh_token','POST',None,
                                {'refresh_token':session['cloud_refresh_token']})
        if not isinstance(refreshed,dict) or not refreshed.get('access_token'):
            raise CloudAPIError('Session expirée. Déconnectez-vous puis reconnectez-vous.',401)
        session['cloud_access_token']=refreshed['access_token']
        session['cloud_refresh_token']=refreshed.get('refresh_token',session['cloud_refresh_token'])
        return _supabase_raw(cfg,path,method,session['cloud_access_token'],payload,prefer)

def cloud_rest(table, params=None, method='GET', session=None, payload=None, prefer=None):
    query=('?'+urlencode(params,doseq=True)) if params else ''
    return supabase_request('/rest/v1/'+table+query,method,session,payload,prefer)

def iso_local(value):
    value=str(value or '').strip()
    if not value: return datetime.now().astimezone().isoformat(timespec='seconds')
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None: dt=dt.astimezone()
        return dt.isoformat(timespec='seconds')
    except Exception:
        return datetime.now().astimezone().isoformat(timespec='seconds')

def date_bounds(date_value):
    try: day=datetime.strptime(str(date_value),'%Y-%m-%d').date()
    except Exception: day=datetime.now().date()
    tz=datetime.now().astimezone().tzinfo
    start=datetime.combine(day,datetime.min.time()).replace(tzinfo=tz)
    end=datetime.combine(day+timedelta(days=1),datetime.min.time()).replace(tzinfo=tz)
    return start.isoformat(timespec='seconds'),end.isoformat(timespec='seconds')

def cloud_http_error(handler, exc):
    status=getattr(exc,'status',400)
    msg=str(exc) or 'La requête cloud a échoué.'
    return handler.send_json({'error':msg},status)

def cloud_function(action, session, payload=None):
    data={'action':action}
    if payload: data.update(payload)
    return supabase_request('/functions/v1/admin-users','POST',session,data)

def make_cloud_sale(d, old=None):
    source=dict(old or {})
    source.update(d)
    typ=str(source.get('device_type','GPS')).strip() or 'GPS'
    calc=calculate_sale(source)
    amount=num(source.get('amount'))
    sold_at=iso_local(source.get('sold_at'))
    return {
        'device_type':typ,
        'device_name':str(source.get('device_name') or ''),
        'client_name':str(source.get('client_name') or '') if typ.upper()=='GPS' else '',
        'mobile':str(source.get('mobile') or '') if typ.upper()=='GPS' else '',
        'device_phone':str(source.get('device_phone') or ''),
        'sim_number':str(source.get('sim_number') or '') if typ.upper()=='GPS' else '',
        'gps_type':str(source.get('gps_type') or '') if typ.upper()=='GPS' else '',
        'address':str(source.get('address') or '') if typ.upper()=='GPS' else '',
        'setup_by':str(source.get('setup_by') or ''),
        'amount':amount,
        'subscription':calc['subscription'],
        'subscription_done':bool(source.get('subscription_done')) if isinstance(source.get('subscription_done'),bool) else str(source.get('subscription_done','')).lower() in ('true','yes','1','oui'),
        'expenses':0,
        'sold_at':sold_at,
        'notes':str(source.get('notes') or ''),
        'device_price':0,
        'setup_price':0,
        'sim_cost':calc['sim_cost'],
        'activation_cost':calc['activation_cost'],
        'benefit':0,
        'next_month_activation':0,
        'subscription_months':calc['subscription_months'] if typ.upper()=='GPS' else 0,
        'actual_subscription_monthly':0,
        'billed_subscription_monthly':calc['billed_subscription_monthly'],
        'total_amount':calc['total_amount'],
    }

def cloud_session_user(session, profile):
    return {'id':profile['id'],'username':profile['username'],'role':profile['role'],
            'full_name':profile.get('full_name') or profile['username'],
            'email':profile.get('email') or ''}

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

    def cloud_get(self,p):
        if p=='/api/health':
            return self.send_json({'ok':True,'app':APP_NAME,'backend':'supabase'})
        u=self.auth()
        if not u: return self.send_json({'error':'Non autorisé'},401)
        try:
            if p=='/api/network':
                return self.send_json({'role':'cloud','server':'Supabase','port':443,'hostname':socket.gethostname(),
                                       'local_ip':local_ip(),'online':True,'access_enabled':True,'max_clients':0})
            if p=='/api/sales':
                rows=cloud_rest('sales',{'select':'*','order':'id.desc','limit':'200'},session=u) or []
                return self.send_json({'items':rows})
            if p=='/api/deposits':
                rows=cloud_rest('deposits',{'select':'*','order':'id.desc','limit':'200'},session=u) or []
                return self.send_json({'items':rows})
            if p=='/api/users':
                if u.get('role')=='Administrateur':
                    result=cloud_function('list',u)
                    return self.send_json({'items':result.get('users',[])})
                rows=cloud_rest('profiles',{'select':'id,username,role,full_name,created_at','order':'username.asc'},session=u) or []
                return self.send_json({'items':rows})
            if p=='/api/dashboard':
                query=parse_qs(urlparse(self.path).query)
                selected=query.get('date',[datetime.now().strftime('%Y-%m-%d')])[0]
                start,end=date_bounds(selected)
                sales_rows=cloud_rest('sales',{'select':'*','and':'(sold_at.gte.'+start+',sold_at.lt.'+end+')','order':'id.desc','limit':'200'},session=u) or []
                dep_rows=cloud_rest('deposits',{'select':'*','and':'(created_at.gte.'+start+',created_at.lt.'+end+')','order':'id.desc','limit':'200'},session=u) or []
                revenue=sum(num(x.get('total_amount') if x.get('total_amount') is not None else x.get('amount')) for x in sales_rows)
                subs=sum(num(x.get('subscription')) for x in sales_rows)
                exp=sum(num(x.get('expenses')) for x in sales_rows)
                dep_total=sum(num(x.get('amount')) for x in dep_rows)
                gps=sum(1 for x in sales_rows if str(x.get('device_type','')).upper()=='GPS')
                star=sum(1 for x in sales_rows if str(x.get('device_type','')).upper()=='STARLINK')
                return self.send_json({'deposits':dep_total,'revenue':revenue,'subscriptions':subs,'expenses':exp,
                                       'gps':gps,'starlink':star,'recent':sales_rows[:8],'recent_deposits':dep_rows[:8]})
            return self.send_json({'error':'Introuvable'},404)
        except CloudAPIError as e:
            return cloud_http_error(self,e)

    def cloud_post(self,p,d):
        if p=='/api/login':
            cfg=load_cloud_config()
            if not cfg.get('enabled'):
                return self.send_json({'error':cfg.get('error') or 'Configuration cloud absente. Exécutez configure_cloud.bat.'},503)
            email=str(d.get('email') or d.get('username') or '').strip().lower()
            password=str(d.get('password') or '')
            if '@' not in email:
                return self.send_json({'error':'Saisissez votre adresse e-mail professionnelle et votre mot de passe.'},400)
            try:
                session_data=supabase_request('/auth/v1/token?grant_type=password','POST',None,
                                              {'email':email,'password':password})
                if not isinstance(session_data,dict) or not session_data.get('access_token') or not session_data.get('user'):
                    return self.send_json({'error':'Réponse de connexion Supabase invalide.'},502)
                cloud_session={'cloud_access_token':session_data['access_token'],
                               'cloud_refresh_token':session_data.get('refresh_token','')}
                uid=session_data['user'].get('id')
                rows=cloud_rest('profiles',{'select':'id,username,full_name,role,created_at','id':'eq.'+str(uid)},session=cloud_session) or []
                if not rows:
                    return self.send_json({'error':'Votre compte est authentifié mais aucun profil employé ne lui est associé. Contactez l’administrateur.'},403)
                profile=rows[0]
                if profile.get('role') not in ('RH','Gestionnaire','Administrateur'):
                    return self.send_json({'error':'Votre rôle d’employé est invalide. Contactez l’administrateur.'},403)
                local_token=secrets.token_urlsafe(32)
                cloud_session.update({'id':profile['id'],'username':profile['username'],'role':profile['role'],
                                      'full_name':profile.get('full_name') or profile['username'],
                                      'email':email,'created_at':profile.get('created_at','')})
                self.sessions[local_token]=cloud_session
                return self.send_json({'token':local_token,'user':cloud_session_user(cloud_session,profile)})
            except CloudAPIError as e:
                if e.status in (400,401): return self.send_json({'error':'Adresse e-mail ou mot de passe incorrect.'},401)
                return cloud_http_error(self,e)

        u=self.auth()
        if not u: return self.send_json({'error':'Non autorisé'},401)
        try:
            if p=='/api/deposits':
                record={'amount':num(d.get('amount')),'department':d.get('department') or 'Finance',
                        'reference':d.get('reference') or '',
                        'deposited_by':d.get('deposited_by') or u.get('full_name') or u.get('username',''),
                        'notes':d.get('notes') or '','created_at':iso_local(d.get('created_at'))}
                cloud_rest('deposits',method='POST',session=u,payload=record,prefer='return=representation')
                return self.send_json({'ok':True})
            m=re.fullmatch(r'/api/deposits/([^/]+)/edit',p)
            if m:
                record={'amount':num(d.get('amount')),'department':d.get('department') or 'Finance',
                        'reference':d.get('reference') or '','deposited_by':d.get('deposited_by') or '',
                        'notes':d.get('notes') or '','created_at':iso_local(d.get('created_at'))}
                cloud_rest('deposits',{'id':'eq.'+m.group(1)},'PATCH',u,record,'return=representation')
                return self.send_json({'ok':True})
            if p=='/api/sales':
                record=make_cloud_sale(d)
                cloud_rest('sales',method='POST',session=u,payload=record,prefer='return=representation')
                return self.send_json({'ok':True})
            m=re.fullmatch(r'/api/sales/([^/]+)/edit',p)
            if m:
                old_rows=cloud_rest('sales',{'select':'*','id':'eq.'+m.group(1),'limit':'1'},session=u) or []
                if not old_rows: return self.send_json({'error':'Vente introuvable.'},404)
                record=make_cloud_sale(d,old_rows[0])
                cloud_rest('sales',{'id':'eq.'+m.group(1)},'PATCH',u,record,'return=representation')
                return self.send_json({'ok':True})
            if p=='/api/users':
                if u.get('role')!='Administrateur': return self.send_json({'error':'Accès réservé à l’administrateur'},403)
                payload={'email':d.get('email',''),'username':d.get('username',''),
                         'full_name':d.get('full_name',''),'role':d.get('role','RH'),
                         'password':d.get('password','')}
                result=cloud_function('create',u,payload)
                return self.send_json({'ok':True,'result':result})
            m=re.fullmatch(r'/api/users/([^/]+)/edit',p)
            if m:
                if u.get('role')!='Administrateur': return self.send_json({'error':'Accès réservé à l’administrateur'},403)
                payload={'id':m.group(1),'username':d.get('username',''),'full_name':d.get('full_name',''),
                         'email':d.get('email',''),'role':d.get('role','RH'),'password':d.get('password','')}
                result=cloud_function('update',u,payload)
                return self.send_json({'ok':True,'result':result})
            return self.send_json({'error':'Introuvable'},404)
        except CloudAPIError as e:
            return cloud_http_error(self,e)
        except Exception as e:
            return self.send_json({'error':'Erreur cloud : '+str(e)[:300]},400)

    def cloud_delete(self,p,u):
        if not u: return self.send_json({'error':'Non autorisé'},401)
        try:
            m=re.fullmatch(r'/api/users/([^/]+)',p)
            if m:
                if u.get('role')!='Administrateur': return self.send_json({'error':'Accès réservé à l’administrateur'},403)
                result=cloud_function('delete',u,{'id':m.group(1)})
                return self.send_json({'ok':True,'result':result})
            m=re.fullmatch(r'/api/sales/([^/]+)',p)
            if m:
                cloud_rest('sales',{'id':'eq.'+m.group(1)},'DELETE',u,None,'return=representation')
                return self.send_json({'ok':True})
            m=re.fullmatch(r'/api/deposits/([^/]+)',p)
            if m:
                cloud_rest('deposits',{'id':'eq.'+m.group(1)},'DELETE',u,None,'return=representation')
                return self.send_json({'ok':True})
            return self.send_json({'error':'Introuvable'},404)
        except CloudAPIError as e:
            return cloud_http_error(self,e)

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
        if cloud_enabled():
            return self.cloud_get(p)
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
        if cloud_enabled():
            return self.cloud_post(p,d)
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
        if cloud_enabled():
            return self.cloud_delete(p,u)
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

def start_local_cloud_api():
    # Every laptop serves its UI/API only on loopback; company records remain in Supabase.
    server=ThreadingHTTPServer(('127.0.0.1',0),API)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server

def show_window(url):
    try:
        import webview
        webview.create_window(APP_NAME,url,width=1500,height=900,min_size=(1100,700),resizable=True)
        webview.start()
    except ImportError:
        print('pywebview is not installed. Run: pip install -r requirements.txt')
        webbrowser.open(url)
        input('Press Enter to exit...')

def main():
    global RUNTIME_ROLE, RUNTIME_SERVER, RUNTIME_PORT
    # Cloud mode is opt-in per laptop via %USERPROFILE%\\WA_Manager_System\\cloud_config.json.
    # Without that file, the previous LAN/SQLite mode remains available as a fallback.
    cloud_cfg=load_cloud_config()
    if os.path.exists(CLOUD_CONFIG_PATH):
        if cloud_cfg.get('error'):
            message='Configuration Supabase invalide : '+str(cloud_cfg['error'])
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0,message,APP_NAME,0x10)
            except Exception:
                print(message)
            raise SystemExit(message)
        if cloud_cfg.get('enabled'):
            server=start_local_cloud_api()
            RUNTIME_ROLE='cloud'; RUNTIME_SERVER='Supabase'; RUNTIME_PORT=443
            url=f'http://127.0.0.1:{server.server_port}/'
            show_window(url)
            return
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

    show_window(url)
if __name__=='__main__':main()
