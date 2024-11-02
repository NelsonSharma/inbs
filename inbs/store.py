# Allow only execution - no importing
#-----------------------------------------------------------------------------------------
from sys import exit
if __name__!='__main__': exit(f'[!] can not import {__name__}.{__file__}')
#-----------------------------------------------------------------------------------------


import os, re, argparse, getpass, logging
#from math import inf
import datetime 
def fnow(format): return datetime.datetime.strftime(datetime.datetime.now(), format)
try:
    from flask import Flask, render_template, request, redirect, url_for, session, abort, send_file
    from flask_wtf import FlaskForm
    from wtforms import SubmitField, MultipleFileField
    from werkzeug.utils import secure_filename
    from wtforms.validators import InputRequired
    from waitress import serve
except: exit(f'[!] The required Flask packages missing:\tFlask>=3.0.2, Flask-WTF>=1.2.1\twaitress>=3.0.0\n  ⇒ pip install Flask Flask-WTF waitress')




#%% Parse Args

parser = argparse.ArgumentParser()
parser.add_argument('--title', type=str, default='Store',        help="a title to display at the login")
parser.add_argument('--root', type=str, default='.',             help="path of root directory")
parser.add_argument('--login', type=str, default='.login',       help="path of login file")

parser.add_argument('--mus', type=str, default='1024TB',         help="Maximum size of uploadable file (hhtp_body_size)")
parser.add_argument('--case', type=int, default=0,               help="case sensetive login uid")

parser.add_argument('--host', type=str, default='0.0.0.0',       help="ip addr 0.0.0.0 for all")
parser.add_argument('--port', type=str, default='8080',          help="port")
parser.add_argument('--mcon', type=int, default=50,              help="max-connections")
parser.add_argument('--threads', type=int, default=4,            help="threads used by waitress")

parser.add_argument('--log', type=str, default='',               help="path of log file")
parser.add_argument('--verbose', type=int, default=2,            help="verbose level in logging")
parsed = parser.parse_args()


#%% Setup logging

# ------------------------------------------------------------------------------------------
LOGFILE = f'{parsed.log}'                               # define log dir - contains all logs
if LOGFILE and parsed.verbose>0: 
# ------------------------------------------------------------------------------------------
    try:
        LOGFILE = os.path.abspath(LOGFILE)
        logging.basicConfig(filename=LOGFILE, level=logging.INFO, format='%(asctime)s - %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(console_handler)
    except: exit(f'[!] Logging could not be setup at {LOGFILE}')
else: LOGFILE = None
# ------------------------------------------------------------------------------------------
if parsed.verbose==0: # no log
    def sprint(msg): pass
    def dprint(msg): pass
    def fexit(msg): exit(msg)
elif parsed.verbose==1: # only server logs
    if LOGFILE is None:
        def sprint(msg): print(msg) 
        def dprint(msg): pass 
        def fexit(msg): exit(msg)
    else:
        def sprint(msg): logging.info(msg) 
        def dprint(msg): pass 
        def fexit(msg):
            logging.error(msg) 
            exit()
elif parsed.verbose>=2: # server and user logs
    if LOGFILE is None:
        def sprint(msg): print(msg) 
        def dprint(msg): print(msg) 
        def fexit(msg): exit(msg)
    else:
        def sprint(msg): logging.info(msg) 
        def dprint(msg): logging.info(msg) 
        def fexit(msg):
            logging.error(msg) 
            exit()
else: raise ZeroDivisionError # impossible


class Table:

    @staticmethod
    def CreateData(*columns):
        data = {None:[f'{col}' for col in columns]} # this is to make sure that col names are always on top
        return data

    @staticmethod
    def Create(columns:tuple, primary_key:str, cell_delimiter=',', record_delimiter='\n'):
        # should be called on a new object after init\
        table = __class__()
        table.data = __class__.CreateData(*columns)
        table.pk = primary_key
        table.pkat = table.data[None].index(table.pk)
        table.cell_delimiter, table.record_delimiter = cell_delimiter, record_delimiter
        return table


    @staticmethod
    def ImportData(path, key_at, cell_delimiter, record_delimiter): 
        with open(path, 'r', encoding='utf-8') as f: 
            s = f.read()
            lines = s.split(record_delimiter)
            cols = lines[0].split(cell_delimiter) #<--- only if None:cols was added as a first entry (using Create method)
            data = {None:cols}
            if isinstance(key_at, str): key_at = cols.index(key_at)
            assert key_at>=0,f'Invlaid key {key_at}'
            for line in lines[1:]:
                if line:
                    cells = line.split(cell_delimiter)
                    data[f'{cells[key_at]}'] = cells
        return data
    
    @staticmethod
    def Import(path, key_at, cell_delimiter=',', record_delimiter='\n'): 
        table = __class__()
        table.data = __class__.ImportData(path, key_at, cell_delimiter, record_delimiter)
        if isinstance(key_at, str): key_at = table[None].index(key_at)
        table.pk = table.data[None][key_at]
        table.pkat = key_at
        table.cell_delimiter, table.record_delimiter = cell_delimiter, record_delimiter
        return table


    @staticmethod
    def ExportData(data, path, cell_delimiter, record_delimiter): 
        with open(path, 'w', encoding='utf-8') as f: 
            for v in data.values(): f.write(cell_delimiter.join(v)+record_delimiter)

    @staticmethod
    def Export(table, path): 
        __class__.ExportData(table.data, path, table.cell_delimiter, table.record_delimiter)

    # get row as dict
    def __call__(self, key): return {k:v for k,v in zip(self[None], self[key])}

    # get row as it is (list)
    def __getitem__(self, key): return self.data[key]

    # set row based on if its a dict or a list (note: key is irrelavant here)
    def __setitem__(self, key, row):
        assert len(row) == len(self[None]), f'Rows are expected to have length {len(self[None])} but got {len(row)}'
        if isinstance(row, dict):
            key = row[self.pk]
            if key is not None: self.data[f'{key}'] = [row[r] for r in self[None]]
        else: 
            key = row[self.pkat]
            if key is not None: self.data[f'{key}'] = list(row)

    # del row based on key
    def __delitem__(self, key):
        if key is not None: del self.data[key]

    def __contains__(self, key): return key in self.data

    # quick export > file
    def __gt__(self, other):__class__.ExportData(self.data, f'{other}', self.cell_delimiter, self.record_delimiter)

    # quick import < file
    def __lt__(self, other): self.data = __class__.ImportData(f'{other}', self.pkat, self.cell_delimiter, self.record_delimiter)

    # total number of rows
    def __len__(self): return len(self.data)-1























































#%% Imports

sprint(f'Starting...')
sprint(f'↪ Logging @ {LOGFILE}')

PYDIR = os.path.abspath(os.path.dirname(__file__))       # script directory of __main__.py
CWDIR = os.path.abspath(os.getcwd())    # location of run

# ------------------------------------------------------------------------------------------
ROOTDIR = f'{parsed.root}'
if not ROOTDIR: fexit(f'[!] Root directory was not specified')
ROOTDIR = os.path.abspath(ROOTDIR)
try: os.makedirs(ROOTDIR, exist_ok=True)
except: fexit(f'[!] Root directory was not found and could not be created')
sprint(f'↪ Root directory is {ROOTDIR}')

#-----------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------
LOGINFILE = f'{parsed.login}' 
if not LOGINFILE: fexit(f'[!] Login-file was not specified')
LOGINFILE = os.path.abspath(LOGINFILE)

sprint(f'↪ Login-file is {LOGINFILE}')
db = Table.Create(columns=('uid', 'pass'), primary_key='uid')

if not os.path.isfile(LOGINFILE):
    if not os.path.exists(LOGINFILE):
        try: 
            THIS_USER = getpass.getuser()
            db[...] = (THIS_USER, '')
            db > LOGINFILE
            sprint(f'↪ New Login-file created @ {LOGINFILE} with user {THIS_USER}')
        except: fexit(f'[!] Login-file was not found and could not be created')
    else: fexit(f'[!] Login-file doesnt exists as a file')

try: 
    db < LOGINFILE
    sprint(f'⇒ Loaded Login-file: {LOGINFILE}')
except : fexit(f'[!] Login-file could not be loaded')
#-----------------------------------------------------------------------------------------

def NEW_SECRET_KEY():
    import time, random
    randx = lambda : random.randint(1111111111, 9999999999)
    r1 = randx()
    for _ in range(datetime.datetime.now().second): _ = randx()
    rd0 = 1.0 + float(datetime.datetime.now().microsecond % 3) + random.random() 
    time.sleep(rd0)
    r2 = randx()
    for _ in range(datetime.datetime.now().microsecond % 9): _ = randx()
    r3 = randx()
    return ':{}:{}:{}:{}:{}:'.format(r1,r2,r3,fnow("%Y%m%d%H%M%S"))
# ------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# password policy
#-----------------------------------------------------------------------------------------
class AuthPolicy:

    def __init__(self, max_len) -> None:
        self.MAX_STR_LEN = int(max_len)

    def VALIDATE_PASS(self, instr):   # a function that can validate the password - returns bool type
        try: assert (len(instr) < self.MAX_STR_LEN) and bool(re.fullmatch("(\w|@|\.)+", instr)) # alpha_numeric @.
        except AssertionError: return False
        return True
    #-----------------------------------------------------------------------------------------
    # uid policy
    def VALIDATE_UID(self, instr):   # a function that can validate the uid - returns bool type
        try: assert (len(instr) < self.MAX_STR_LEN) and bool(re.fullmatch("(\w)+", instr)) # alpha_numeric 
        except AssertionError: return False
        return True
    #-----------------------------------------------------------------------------------------
    #-----------------------------------------------------------------------------------------
    # name policy
    def VALIDATE_NAME(self, instr): return  (len(instr) >0) and (len(instr) < self.MAX_STR_LEN) and \
        bool(re.fullmatch("((\w)(\w|\s)*(\w))|(\w)", instr)) # alpha-neumeric but no illegal spaces before or after
    #-----------------------------------------------------------------------------------------

def str2bytes(size):
    sizes = dict(KB=2**10, MB=2**20, GB=2**30, TB=2**40)
    return int(float(size[:-2])*sizes.get(size[-2:].upper(), 0))


def DISPLAY_SIZE_READABLE(mus):
    # find max upload size in appropiate units
    mus_kb = mus/(2**10)
    if len(f'{int(mus_kb)}') < 4:
        mus_display = f'{mus_kb:.2f} KB'
    else:
        mus_mb = mus/(2**20)
        if len(f'{int(mus_mb)}') < 4:
            mus_display = f'{mus_mb:.2f} MB'
        else:
            mus_gb = mus/(2**30)
            if len(f'{int(mus_gb)}') < 4:
                mus_display = f'{mus_gb:.2f} GB'
            else:
                mus_tb = mus/(2**40)
                mus_display = f'{mus_tb:.2f} TB'
    return mus_display

AP = AuthPolicy(100)

# print(f'{LOGFILE=}', f'{PYDIR=}', f'{CWDIR=}', f'{ROOTDIR=}', f'{LOGINFILE=}', f'{SECRETFILE=}')


#%%






















# ------------------------------------------------------------------------------------------
# html pages
# ------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------
# Create HTML
# ------------------------------------------------------------------------------------------

# ******************************************************************************************
CSS_TEMPLATES = dict(
# ****************************************************************************************** 0b7daa
style = """

.title{
    color: #000000;
    font-size: xxx-large;
    font-weight: bold;
    font-family:monospace;    
}

.txt_login{

    text-align: center;
    font-family:monospace;

    box-shadow: inset #abacaf 0 0 0 2px;
    border: 0;
    background: rgba(0, 0, 0, 0);
    appearance: none;
    position: relative;
    border-radius: 3px;
    padding: 9px 12px;
    line-height: 1.4;
    color: rgb(0, 0, 0);
    font-size: 16px;
    font-weight: 400;
    height: 40px;
    transition: all .2s ease;
    :hover{
        box-shadow: 0 0 0 0 #fff inset, #1de9b6 0 0 0 2px;
    }
    :focus{
        background: #fff;
        outline: 0;
        box-shadow: 0 0 0 0 #fff inset, #1de9b6 0 0 0 3px;
    }
}
::placeholder {
    color: #888686;
    opacity: 1;
    font-weight: bold;
    font-style: oblique;
    font-family:monospace;   
}
.btn_login {
    padding: 2px 10px 2px 10px;
    background-color: #060472; 
    color: #FFFFFF;
    font-weight: bold;
    font-size: large;
    border-radius: 5px;
    font-family:monospace;
    text-decoration: none;
    border-style:  none;
}

.btn_home{
    padding: 2px 10px 2px 10px;
    background-color: #089a28; 
    color: #FFFFFF;
    font-weight: bold;
    font-size: large;
    border-radius: 5px;
    font-family:monospace;
    text-decoration: none;
}

.btn_board {
    padding: 2px 10px 2px 10px;
    background-color: #934377; 
    border-style: none;
    color: #FFFFFF;
    font-weight: bold;
    font-size: large;
    border-radius: 5px;
    font-family:monospace;
    text-decoration: none;
}

.userword{
    color: #12103c;
    font-weight: bold;
    font-family:monospace;    
    font-size: xxx-large;
}

.files_status{
    font-weight: bold;
    font-size: x-large;
    font-family:monospace;
}

.files_list_up{
    padding: 10px 10px;
    background-color: #fcffa6; 
    color: #080000;
    font-size: x-large;
    border-radius: 10px;
    font-family:monospace;
    text-decoration: none;
}

.files_list_down{
    padding: 10px 10px;
    background-color: #ececec; 
    color: #080000;
    font-size: x-large;
    font-weight: bold;
    border-radius: 10px;
    font-family:monospace;
    text-decoration: none;
}

.msg_login{
    color: #060472; 
    font-size: large;
    font-weight: bold;
    font-family:monospace;    
    animation-duration: 3s; 
    animation-name: fader_msg;
}
@keyframes fader_msg {from {color: #ffffff;} to {color: #060472; } }


#file {
    border-style: solid;
    border-radius: 10px;
    font-family:monospace;
    background-color: #232323;
    border-color: #232323;
    color: #FFFFFF;
    font-size: small;
}
#submit {
    padding: 2px 10px 2px;
    background-color: #232323; 
    color: #FFFFFF;
    font-family:monospace;
    font-weight: bold;
    font-size: large;
    border-style: solid;
    border-radius: 10px;
    border-color: #232323;
    text-decoration: none;
    font-size: small;
}
#submit:hover {
  box-shadow: 0 12px 16px 0 rgba(0, 0, 0,0.24), 0 17px 50px 0 rgba(0, 0, 0,0.19);
}

"""
)


# ******************************************************************************************
HTML_TEMPLATES = dict(
# ******************************************************************************************

# ******************************************************************************************

login = """
<html>
    <head>
        <meta charset="UTF-8">
        <title> {{ config.title }} </title>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">  
    </head>
    <body>
    <!-- ---------------------------------------------------------->
    </br>
    <!-- ---------------------------------------------------------->

    <div align="center">
        <br>
        <div class="title">{{ config.title }}</div>
        <br>
        <br>
        <form action="{{ url_for('route_login') }}" method="post">
            <br>
            <div style="font-size: x-large;">{{ warn }}</div>
            <br>
            <div class="msg_login">{{ msg }}</div>
            <br>
            <input id="uid" name="uid" type="text" placeholder="... user-id ..." class="txt_login"/>
            <br>
            <br>
            <input id="passwd" name="passwd" type="password" placeholder="... password ..." class="txt_login"/>
            <br>
            <br>
            <input type="submit" class="btn_login" value="Login"> 
            <br>
            <br>
        </form>
    </div>

    <!-- ---------------------------------------------------------->
    <!-- ---------------------------------------------------------->
    </body>
</html>
""",
#******************************************************************************************
store = """
<html>
    <head>
        <meta charset="UTF-8">
        <title> {{ config.title }} | {{ session.uid }} </title>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">           
    </head>
    <body>
    <!-- ---------------------------------------------------------->
    </br>
    <!-- ---------------------------------------------------------->
    
    <div align="left" style="padding: 20px;">
        <a href="{{ url_for('route_logout') }}" class="btn_login">Logout</a>
        <br>
        <div class="userword">{{session.uid}}</div>
        <br>
        <!-- Breadcrumb for navigation -->
        <div class="files_status">
            {% if subpath %}
                <a href="{{ url_for('route_store') }}" class="btn_home">{{ config.rootname }}</a>{% for part in subpath.split('/') %}🔹<a href="{{ url_for('route_store', subpath='/'.join(subpath.split('/')[:loop.index])) }}" class="btn_board">{{ part }}</a>{% endfor %} <a href="{{ url_for('route_store', subpath=subpath, get='') }}" >⬇️</a> <a href="{{ url_for('route_store', subpath=subpath, del='') }}" >❌</a> 
            {% else %}
                <a href="{{ url_for('route_store') }}" class="btn_home">{{ config.rootname }}</a>
            {% endif %}
        </div>
        <!-- Directory Listing -->
        <br>
        <div class="files_list_up">
            {% for dir in dirs %}
            <a href="{{ url_for('route_store', subpath=subpath + '/' + dir) }}" class="btn_board">{{ dir }}</a>
            {% endfor %}
        </div>
        <hr>
        <div class="files_list_down">
            <ol>
            {% for file in files %}
            <li>
            <a href="{{ url_for('route_store', subpath=subpath + '/' + file, get='') }}" >⬇️</a> 
            <a href="{{ url_for('route_store', subpath=subpath + '/' + file, del='') }}" >❌</a> 
            <a href="{{ url_for('route_store', subpath=subpath + '/' + file) }}" target="_blank">{{ file }}</a>
            </li>
            
            {% endfor %}
            </ol>
        </div>
        <br>
        <br>
    </div>

    <!-- ---------------------------------------------------------->
    </br>
    <!-- ---------------------------------------------------------->
    </body>
</html>
""",
)
# ******************************************************************************************

# ******************************************************************************************
# ******************************************************************************************


TEMPLATES_DIR, STATIC_DIR = os.path.join(PYDIR, "templates"), os.path.join(PYDIR, "static")
os.makedirs(TEMPLATES_DIR, exist_ok=True)
#sprint(f'↪ Creating html templates @ {TEMPLATES_DIR}')
for k,v in HTML_TEMPLATES.items():
    h = os.path.join(TEMPLATES_DIR, f"{k}.html")
    with open(h, 'w', encoding='utf-8') as f: f.write(v)
os.makedirs(STATIC_DIR, exist_ok=True)
#sprint(f'↪ Creating css templates @ {STATIC_DIR}')
for k,v in CSS_TEMPLATES.items():
    h = os.path.join(STATIC_DIR, f"{k}.css")
    with open(h, 'w', encoding='utf-8') as f: f.write(v)
sprint(f'↪ Created html/css templates @ {PYDIR}')


# ******************************************************************************************
#%%
# ------------------------------------------------------------------------------------------
# application setting and instance
# ------------------------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key =          NEW_SECRET_KEY()
app.config['root'] =      ROOTDIR
app.config['rootname'] =  os.path.basename(ROOTDIR)
app.config['title'] =     parsed.title
app.config['case'] =      parsed.case
app.config['hide'] =      parsed.hide
# ------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------
@app.route('/', methods =['GET', 'POST'])
def route_login():
    LOGIN_NEED_TEXT =       '🔒'
    LOGIN_FAIL_TEXT =       '❌'     
    LOGIN_NEW_TEXT =        '🔥'
    LOGIN_CREATE_TEXT =     '🔑'    
    
    if request.method == 'POST' and 'uid' in request.form and 'passwd' in request.form:
        global db
        in_uid = f"{request.form['uid']}"
        in_passwd = f"{request.form['passwd']}"
        in_query = in_uid if not app.config['case'] else (in_uid.upper() if app.config['case']>0 else in_uid.lower())
        valid_query = AP.VALIDATE_UID(in_query)
        record = None if not valid_query else (db[in_query] if (in_query in db) else ...)
        if (record is None) or (record is ...):  warn, msg = LOGIN_FAIL_TEXT, f'[{in_uid}] Not a valid user'
        else: 
            access, uid, passwd = record
            if not passwd: # fist login
                if in_passwd: # new password provided
                    if AP.VALIDATE_PASS(in_passwd): # new password is valid
                        db[uid][-1]=in_passwd 
                        warn = LOGIN_CREATE_TEXT
                        msg = f'[{in_uid}] New password was created successfully'
                        dprint(f'● {in_uid} just joined via {request.remote_addr}')
                    else: # new password is invalid valid 
                        warn, msg = LOGIN_NEW_TEXT, f'[{in_uid}] New password is invalid - can use alpha-numeric, underscore and @-symbol'
                else: #new password not provided                
                    warn, msg = LOGIN_NEW_TEXT, f'[{in_uid}] New password required - can use alpha-numeric, underscore and @-symbol'
                                           
            else: # re login
                if in_passwd: # password provided 
                    if in_passwd==passwd:
                        session['has_login'] = True
                        session['uid'] = uid
                        session['access'] = access 
                        dprint(f'● {session["uid"]} has logged in via {request.remote_addr}') 
                        return redirect(url_for('route_store'))
                    else:  
                        warn, msg = LOGIN_FAIL_TEXT, f'[{in_uid}] Password mismatch'             
                else: # password not provided
                    warn, msg = LOGIN_FAIL_TEXT, f'[{in_uid}] Password not provided'
    else:
        if session.get('has_login', False):  return redirect(url_for('route_store'))
        warn, msg = LOGIN_NEED_TEXT, f'Login to continue'
        
        
    return render_template('login.html', msg = msg,  warn = warn)

@app.route('/logout')
def route_logout():
    r""" logout a user and redirect to login page """
    if not session.get('has_login', False):  return redirect(url_for('route_login'))
    if not session.get('uid', False): return redirect(url_for('route_login'))
    if session['has_login']:  dprint(f'● {session["uid"]} has logged out via {request.remote_addr}') 
    else: dprint(f'✗ {session["uid"]}was removed due to invalid uid via {request.remote_addr}') 
    session.clear()
    return redirect(url_for('route_login'))
# ------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------
@app.route('/store', methods =['GET', 'POST'])
@app.route('/store/', methods =['GET', 'POST'])
@app.route('/store/<path:subpath>', methods =['GET', 'POST'])
def route_store(subpath=""):
    if not session.get('has_login', False): return redirect(url_for('route_login'))
    
    abs_path = os.path.join(app.config['root'], subpath)
    if not os.path.exists(abs_path): return abort(404)

    if os.path.isdir(abs_path):
        items = os.listdir(abs_path)
        if app.config['hide']: items = [item for item in items if not item.startswith('.')]
        dirs = [item for item in items if os.path.isdir(os.path.join(abs_path, item))]
        files = [item for item in items if os.path.isfile(os.path.join(abs_path, item))]
        return render_template('store.html', dirs=dirs, files=files, subpath=subpath)
    elif os.path.isfile(abs_path): 
        if request.args:
            if TOKEN_DOWNLOAD in request.args:
                dprint(f'● {session["uid"]} downloaded {abs_path} via {request.remote_addr}')
                return send_file(abs_path, as_attachment=True)
        else : return send_file(abs_path, as_attachment=False)
    else: return abort(404)




# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#<-------------------DO NOT WRITE ANY NEW CODE AFTER THIS
endpoint = f'{parsed.host}:{parsed.port}' if parsed.host!='0.0.0.0' else f'localhost:{parsed.port}'
sprint(f'◉ http://{endpoint}')
start_time = datetime.datetime.now()
sprint('◉ start server @ [{}]'.format(start_time))
serve(app, # https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html
    host = parsed.host,          
    port = parsed.port,          
    url_scheme = 'http',     
    threads = parsed.threads,    
    connection_limit = parsed.mcon,
    max_request_body_size = FP.MAX_UPLOAD_SIZE,
)
#<-------------------DO NOT WRITE ANY CODE AFTER THIS
end_time = datetime.datetime.now()
sprint('◉ stop server @ [{}]'.format(end_time))
try: 
    db > LOGINFILE
    sprint('↷ persisted login-db')
except: sprint('↷ could not persist login-db')

sprint(f'↪ Cleaning up html/css templates...')
try:
    for k,v in HTML_TEMPLATES.items():
        h = os.path.join(TEMPLATES_DIR, f"{k}.html")
        if  os.path.isfile(h) : os.remove(h)
    #sprint(f'↪ Removing css templates @ {STATIC_DIR}')
    for k,v in CSS_TEMPLATES.items():
        h = os.path.join(STATIC_DIR, f"{k}.css")
        if os.path.isfile(h): os.remove(h)
    os.removedirs(TEMPLATES_DIR)
    os.removedirs(STATIC_DIR)
    sprint(f'↪ Removed html/css templates @ {PYDIR}')
except:
    sprint(f'↪ Could not remove html/css templates @ {PYDIR}')
sprint('◉ server up-time was [{}]'.format(end_time - start_time))
sprint(f'...Finished!')
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@