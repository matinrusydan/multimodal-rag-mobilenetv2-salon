"""Dedicated ChatGPT-plan OAuth login. Never reads Codex/browser credentials.

CLI: python -m app.chatgpt_auth login|status|models|logout
"""
from __future__ import annotations
import argparse,base64,contextlib,ctypes,hashlib,json,os,secrets,time,uuid,webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlencode,urlsplit
import httpx

ISSUER='https://auth.openai.com'
RESOURCE='https://api.openai.com/v1'
AUTHORIZE=ISSUER+'/api/accounts/authorize'
TOKEN=ISSUER+'/api/accounts/oauth/token'
PLAN_SCOPE='chatgpt.tokens.use.direct'


def auth_path():
    # Turbo's strict environment can omit LOCALAPPDATA/USERPROFILE. Resolve the
    # Windows user folder through the OS so CLI and server share one location.
    if os.name=='nt':
        from ctypes import wintypes
        buffer=ctypes.create_unicode_buffer(32768)
        shell=ctypes.WinDLL('shell32')
        shell.SHGetFolderPathW.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR]
        shell.SHGetFolderPathW.restype=ctypes.c_long
        if shell.SHGetFolderPathW(None,0x001C,None,0,buffer)!=0:
            raise RuntimeError('Folder data pengguna Windows tidak dapat ditemukan')
        base=Path(buffer.value)
    else:
        base=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    return base/'RAGSalon'/'chatgpt-plan.credentials'


def _protect(raw:bytes, decrypt=False):
    if os.name!='nt':return raw
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buf=ctypes.create_string_buffer(raw)
    src=Blob(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))); dest=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    function=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype=wintypes.BOOL
    if not function(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dest)):
        raise RuntimeError('Penyimpanan kredensial Windows gagal')
    try:return ctypes.string_at(dest.data,dest.size)
    finally:
        kernel=ctypes.WinDLL('kernel32');kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree(dest.data)


def load():
    path=auth_path()
    return json.loads(_protect(path.read_bytes(),True)) if path.exists() else {}


def save(profile):
    path=auth_path();path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(_protect(json.dumps(profile).encode()))
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


@contextlib.contextmanager
def session_lock():
    path=auth_path().with_suffix('.lock');path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_RDWR|os.O_CREAT,0o600)
    with os.fdopen(fd,'r+b') as stream:
        stream.write(b'0');stream.flush();stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream,fcntl.LOCK_UN)


def _decode(value):return base64.urlsafe_b64decode(value+'='*(-len(value)%4))


def verify_identity(token,client_id,nonce,jwks):
    from cryptography.hazmat.primitives.asymmetric import rsa,padding
    from cryptography.hazmat.primitives import hashes
    head,body,sig=token.split('.')
    header=json.loads(_decode(head));claims=json.loads(_decode(body))
    if header.get('alg')!='RS256':raise ValueError('Algoritma ID token tidak didukung')
    key=next((k for k in jwks['keys'] if k.get('kid')==header.get('kid') and k.get('kty')=='RSA'),None)
    if not key:raise ValueError('Kunci tanda tangan ID token tidak ditemukan')
    pub=rsa.RSAPublicNumbers(int.from_bytes(_decode(key['e']),'big'),int.from_bytes(_decode(key['n']),'big')).public_key()
    pub.verify(_decode(sig),(head+'.'+body).encode(),padding.PKCS1v15(),hashes.SHA256())
    aud=claims.get('aud');aud=[aud] if isinstance(aud,str) else aud
    if claims.get('iss')!=ISSUER or not isinstance(aud,list) or client_id not in aud:
        raise ValueError('Issuer/audience ID token tidak sesuai')
    if not isinstance(claims.get('exp'),(int,float)) or claims['exp']<=time.time() or not claims.get('sub'):
        raise ValueError('ID token tidak valid atau kedaluwarsa')
    if nonce is not None and claims.get('nonce')!=nonce:raise ValueError('Nonce ID token tidak sesuai')
    if len(aud)>1 and claims.get('azp')!=client_id:raise ValueError('Authorized party tidak sesuai')
    if claims.get('nbf',0)>time.time()+30:raise ValueError('ID token belum berlaku')
    return claims


def _json(response):
    if response.status_code>=400:
        raise RuntimeError('Permintaan autentikasi gagal (HTTP '+str(response.status_code)+'); login ulang atau periksa izin akun.')
    return response.json()


def _jwks(client):
    metadata=_json(client.get(ISSUER+'/.well-known/openid-configuration'))
    url=metadata.get('jwks_uri','')
    if metadata.get('issuer')!=ISSUER or urlsplit(url).scheme!='https' or urlsplit(url).hostname!='auth.openai.com':
        raise ValueError('Metadata OIDC tidak sesuai origin resmi')
    return _json(client.get(url))


def _apply_tokens(profile,tokens):
    scopes=set(tokens.get('scope','').split())
    if PLAN_SCOPE not in scopes or tokens.get('token_type','').lower()!='bearer' or not tokens.get('access_token'):
        raise ValueError('Akun belum memberikan izin penggunaan paket ChatGPT')
    result={**profile,**{k:tokens[k] for k in ['access_token','refresh_token','id_token'] if tokens.get(k)},
            'scopes':sorted(scopes),'expires_at':time.time()+float(tokens['expires_in'])}
    return result


def access_token():
    with session_lock():
        profile=load()
        if not profile.get('access_token') or PLAN_SCOPE not in profile.get('scopes',[]):
            raise RuntimeError('Login aplikasi diperlukan: python -m app.chatgpt_auth login')
        if profile.get('expires_at',0)<=time.time()+60:
            if not profile.get('refresh_token'):raise RuntimeError('Sesi habis; login ulang diperlukan')
            with httpx.Client(timeout=30) as client:
                result=_json(client.post(TOKEN,data={'grant_type':'refresh_token','client_id':profile['client_id'],
                        'refresh_token':profile['refresh_token'],'resource':RESOURCE}))
                # OAuth may omit scope on refresh; omission retains the existing grant.
                result.setdefault('scope',' '.join(profile['scopes']))
                if result.get('id_token'):
                    identity=verify_identity(result['id_token'],profile['client_id'],None,_jwks(client))
                    if identity['sub']!=profile['subject']:raise ValueError('Identitas akun berubah saat refresh')
                profile=_apply_tokens(profile,result);save(profile)
        return profile['access_token']


def _callback_port(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('Port callback harus antara 1 dan 65535') from None
    if isinstance(value, bool) or str(port) != str(value) or not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError('Port callback harus antara 1 dan 65535')
    return port


def login(timeout=180, *, no_browser=False, callback_port=None):
    port = 0 if callback_port is None else _callback_port(callback_port)
    if timeout <= 0:
        raise ValueError('Batas waktu login harus positif')
    with session_lock():
        profile=load();profile.setdefault('host_id','urn:uuid:'+str(uuid.uuid4()));save(profile)
        state,nonce,verifier=[secrets.token_urlsafe(32) for _ in range(3)]
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        result={}
        class Callback(BaseHTTPRequestHandler):
            def log_message(self,*args):pass  # Callback URLs contain authorization codes.
            def do_GET(self):
                parsed=urlsplit(self.path);q=parse_qs(parsed.query)
                if parsed.path!='/auth/callback' or q.get('state')!=[state]:
                    self.send_response(400);self.end_headers();return
                result.update({k:v[0] for k,v in q.items()});self.send_response(200)
                self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers()
                self.wfile.write(b'Kembali ke terminal RAG Salon untuk melihat hasil verifikasi login.')
        with HTTPServer(('127.0.0.1',port),Callback) as server:
            redirect=f'http://127.0.0.1:{server.server_port}/auth/callback'
            params={'client_id':profile.get('client_id','dynamic_agent_client'),'ext_agent_host_id':profile['host_id'],
                    'response_type':'code','redirect_uri':redirect,'scope':'openid profile email offline_access resource.invoke '+PLAN_SCOPE,
                    'resource':RESOURCE,'state':state,'nonce':nonce,'code_challenge_method':'S256','code_challenge':challenge}
            if not profile.get('client_id'):params['agent_name_hint']='RAG Salon'
            authorization_url = AUTHORIZE+'?'+urlencode(params)
            if no_browser:
                # Only the authorization URL is printed, never callback URLs/codes.
                print(authorization_url, flush=True)
            else:
                print('Continue with ChatGPT — setujui penggunaan paket hanya untuk aplikasi RAG Salon di browser.')
                if not webbrowser.open(authorization_url):
                    raise RuntimeError('Browser tidak dapat dibuka; jalankan login di sesi desktop interaktif')
            deadline=time.monotonic()+timeout;server.timeout=1
            while not result and time.monotonic()<deadline:server.handle_request()
        if not result:raise RuntimeError('Login melewati batas waktu; jalankan login ulang')
        if result.get('error') or not result.get('code'):raise RuntimeError('Login dibatalkan atau izin tidak diberikan')
        issued=result.get('client_id',profile.get('client_id'))
        if not issued or issued=='dynamic_agent_client' or (profile.get('client_id') and issued!=profile['client_id']):
            raise ValueError('Client ID hasil login tidak sesuai')
        # Persist registration if token exchange must be retried; never activate unverified credentials.
        profile['client_id']=issued;save(profile)
        with httpx.Client(timeout=30) as client:
            tokens=_json(client.post(TOKEN,data={'grant_type':'authorization_code','client_id':issued,
                         'code':result['code'],'code_verifier':verifier,'redirect_uri':redirect,'resource':RESOURCE}))
            identity=verify_identity(tokens.get('id_token',''),issued,nonce,_jwks(client))
        if profile.get('subject') and identity['sub']!=profile['subject']:raise ValueError('Akun berbeda dari sesi tersimpan')
        profile.update(subject=identity['sub'],email=identity.get('email'))
        save(_apply_tokens(profile,tokens))
        if not no_browser:
            print('Login dan izin paket terverifikasi. Jalankan models untuk melihat pilihan model; inferensi belum diuji.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['login','status','models','logout'])
    parser.add_argument('--no-browser', action='store_true', help='Cetak URL login tanpa membuka browser')
    parser.add_argument('--callback-port', type=_callback_port, help='Port callback loopback (1–65535)')
    args=parser.parse_args()
    if args.command != 'login' and (args.no_browser or args.callback_port is not None):
        parser.error('--no-browser dan --callback-port hanya berlaku untuk login')
    try:
        if args.command=='login':login(no_browser=args.no_browser, callback_port=args.callback_port)
        elif args.command=='status':
            p=load();print(json.dumps({'connected':bool(p.get('access_token')),
                 'plan_permission':PLAN_SCOPE in p.get('scopes',[]),'expired':p.get('expires_at',0)<=time.time()}))
        elif args.command=='models':
            with httpx.Client(timeout=30) as client:
                data=_json(client.get(RESOURCE+'/models',headers={'Authorization':'Bearer '+access_token()}))
            print(json.dumps([{'slug':m['slug'],'display_name':m.get('display_name',m['slug'])} for m in data.get('models',[]) if m.get('visibility')=='list'],indent=2))
        else:
            with session_lock():
                p=load();revoked=not p.get('refresh_token')
                if p.get('refresh_token'):
                    try:
                        with httpx.Client(timeout=30) as client:
                            meta=_json(client.get(ISSUER+'/.well-known/openid-configuration'));url=meta.get('revocation_endpoint','')
                            if urlsplit(url).scheme!='https' or urlsplit(url).hostname!='auth.openai.com':raise ValueError('Revocation origin tidak sesuai')
                            revoked=client.post(url,data={'token':p['refresh_token'],'token_type_hint':'refresh_token','client_id':p['client_id']}).status_code==200
                    except Exception:revoked=False
                save({k:p[k] for k in ['host_id','client_id','subject'] if k in p})
            print('Logout lokal selesai. Revokasi remote '+('terkonfirmasi.' if revoked else 'belum terkonfirmasi; putuskan aplikasi melalui pengaturan ChatGPT.'))
    except Exception as exc:
        parser.exit(1,'Proses gagal: '+type(exc).__name__+'. Periksa koneksi/izin akun dan dokumentasi setup; kredensial tidak dicetak.\n')


if __name__=='__main__':main()
