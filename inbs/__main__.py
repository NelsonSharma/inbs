#-----------------------------------------------------------------------------------------
from sys import exit
if __name__!='__main__': exit(f'[!] can not import {__name__}.{__file__}')
#-----------------------------------------------------------------------------------------
#%% Arg-parse
import os, argparse, datetime, logging

parser = argparse.ArgumentParser()
parser.add_argument('--base',           type=str, default='', help="path to base dir, defaults to current directory"     )
parser.add_argument('--template',       type=str, default='lab', help="classic/[lab]/reveal"   )
parser.add_argument('--home',           type=str, default='', help="home page if not specified, creates a new notebook with the same name as the base dir"   )
parser.add_argument('--no_script',      type=int, default=0, help="[default=False] if true, remove any embedded <script> tags")
parser.add_argument('--no_files',       type=int, default=0, help="[default=False] if true, prevents downloading files - only notebooks can be viewed and downloaded ")
parser.add_argument('--log',            type=str, default='', help="log file name - keep empty for no logging")
parser.add_argument('--host',           type=str, default='0.0.0.0', )
parser.add_argument('--port',           type=str, default='8888', )
parser.add_argument('--threads',        type=int, default=10, )
parser.add_argument('--max_connect',    type=int, default=500, )
parser.add_argument('--max_size',       type=str, default='1024MB', help="size of http body"   )
# Notebook decorations
parser.add_argument('--dtext',          type=str, default='📥️', help="text for download link"   )
parser.add_argument('--ttext',          type=str, default='🔝', help="text for top link"   )
parser.add_argument('--htext',          type=str, default='🏠', help="text for home link"   )
parser.add_argument('--header',         type=int, default=0, help="shows text in the header"   )
parsed = parser.parse_args()

#%% Logging
LOGFILE = f'{parsed.log}'
if LOGFILE: 
    try:
        logging.basicConfig(filename=LOGFILE, filemode='a', level=logging.INFO, format='%(asctime)s - %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(console_handler)
    except: exit(f'[!] Logging could not be setup at {LOGFILE}')
    def sprint(msg): logging.info(msg) 
else:
    def sprint(msg): print(msg) 

#%% imports
import nbconvert, os
from bs4 import BeautifulSoup
from flask import Flask, request, abort, redirect, url_for, send_file
from waitress import serve

#%% Common
str2bytes_sizes = dict(BB=2**0, KB=2**10, MB=2**20, GB=2**30, TB=2**40)
def str2bytes(size): return int(float(size[:-2])*str2bytes_sizes.get(size[-2:].upper(), 0))

style_actions = """
.btn_header {
    background-color: #FFFFFF; 
    margin: 0px 0px 0px 6px;
    padding: 12px 6px 12px 6px;
    border-style: solid;
    border-width: thin;
    border-color: #000000;
    color: #000000;
    font-weight: bold;
    font-size: medium;
    border-radius: 5px;
}

.btn_actions {
    background-color: #FFFFFF; 
    padding: 2px 2px 2px 2px;
    margin: 5px 5px 5px 5px;
    border-style: solid;
    border-color: silver;
    border-width: thin;
    color: #000000;
    font-weight: bold;
    font-size: medium;
    border-radius: 2px;
}
"""

def nb2html(source_notebook, html_title=None, 
            template_name='lab', no_script=False, favicon=True, 
            hlink='home', header=0, tlink='top', dlink='download', durl='#', align='left'):
    # ==============================================================
    if html_title is None:
        html_title = os.path.basename(source_notebook)
        if html_title.lower().endswith(".ipynb"): html_title = html_title[:-6]
    page, _ = nbconvert.HTMLExporter(template_name=template_name) \
            .from_file(source_notebook, dict(metadata=dict(name = f'{html_title}')),) 
    soup = BeautifulSoup(page, 'html.parser')
    # ==============================================================
    
    if no_script:
        for script in soup.find_all('script'): script.decompose()  # Find all script tags and remove them
    
    if favicon:
        link_tag = soup.new_tag('link')
        link_tag['rel'] = 'icon'
        link_tag['href'] = 'favicon.ico'
        soup.head.insert(0, link_tag)

    if tlink or hlink or dlink or header: 
        style_tag = soup.new_tag('style')
        style_tag['type'] = 'text/css'
        style_tag.string = style_actions
        soup.head.insert(0, style_tag)


        if hlink or dlink or header:
            ndiv = soup.new_tag('div')
            ndiv['align'] = f'{align}'
            html_string = ""
            if hlink: html_string += f'<a class="btn_actions" href="/">{hlink}</a>' 
            if dlink: html_string += f'<a class="btn_actions" href="{durl}">{dlink}</a>' 
            if header: html_string += f'<span class="btn_header">{html_title} @ ./{os.path.relpath(source_notebook, app.config['base'])}</span>'
            html_string += f'<br><hr>'
            nstr = BeautifulSoup(html_string, 'html.parser')
            ndiv.append(nstr) 
            soup.body.insert(0, ndiv)

        if tlink:
            ndiv = soup.new_tag('div')
            ndiv['align'] = f'{align}'
            html_string = f'<hr><a class="btn_actions" href="#">{tlink}</a><br>'
            nstr = BeautifulSoup(html_string, 'html.parser')
            ndiv.append(nstr) 
            soup.body.append(ndiv)

    # ==============================================================
    # final_page = soup.prettify()
    # ==============================================================
    return soup.prettify()

def new_notebook(heading="", nbformat=4, nbformat_minor=2):
    return '{"cells": [{"cell_type": "markdown","metadata": {},"source": [ "# '+str(heading)+'" ] } ], "metadata": { }, "nbformat": '+str(nbformat)+', "nbformat_minor": '+str(nbformat_minor)+'}'

#%% App Setup 

BASE = os.path.abspath(parsed.base)
try: os.makedirs(BASE, exist_ok=True)
except: 
    sprint(f'No directory found at {BASE}, using current directory...')
    BASE = os.path.abspath(os.getcwd())

favicon_path = os.path.join( BASE, f"favicon.ico") 
if not os.path.exists(favicon_path):
    try: 
        from . import FAVICON
        with open( favicon_path, 'wb') as f: f.write((b''.join([i.to_bytes() for i in FAVICON])))
    except ModuleNotFoundError: pass

sprint(f'⇒ Serving from directory {BASE}')
EXT = ".ipynb"
PH = f'{parsed.home}'
if not PH: PH=os.path.basename(BASE)
HOME = f'{PH}{EXT}'
HOME_PATH = os.path.join(BASE, HOME)
if not os.path.isfile(HOME_PATH):
    try: 
        with open(HOME_PATH, 'w') as f: f.write(new_notebook(os.path.basename(BASE)))
    except: exit(f'The home page at {HOME_PATH} was not found and could not be created.')
if not os.path.isfile(HOME_PATH): exit(f'Home page "{HOME}" not found at {HOME_PATH}.')

app = Flask(__name__, static_folder=BASE, template_folder=BASE)
app.config['base'] = BASE
app.config['template'] = parsed.template
app.config['dtext'] = parsed.dtext
app.config['ttext'] = parsed.ttext
app.config['htext'] = parsed.htext
app.config['header'] = int(parsed.header)
app.config['home'] = HOME
app.config['title'] = os.path.basename(BASE)
app.config['ext'] = EXT
app.config['query_refresh'] = "!"
app.config['query_download'] = "?"
app.config['query_clear'] = "~"
app.config['no_script'] = bool(parsed.no_script)
app.config['no_files'] = bool(parsed.no_files)

loaded_pages = dict()

#%% Routes Section

@app.route('/', methods =['GET'], defaults={'query': ''})
@app.route('/<path:query>')
def route_home(query):
    refresh = app.config['query_refresh'] in request.args
    download = app.config['query_download'] in request.args
    clear = app.config['query_clear'] in request.args
    base, ext, home = app.config['base'], app.config['ext'], app.config['home']
    tosend = False
    
    if ('.' in os.path.basename(query)):    tosend = (not query.lower().endswith(ext))
    else:                                   query += ext #---> auto add extension
    if ext==query: 			                query=home

    showdlink = not((query==home) or (query==ext))
    #sprint (f'[{"🔸" if showdlink else "🔹"}]{request.remote_addr}\t[{request.method}] {request.url}')
    if showdlink: sprint (f'({request.remote_addr})\t[{request.method}] {request.url}')

    requested = os.path.join(base, query) # Joining the base and the requested path
    if not ((os.path.isfile(requested)) and (not os.path.relpath(requested, base).startswith(base))): return abort(404)
    else:
        if tosend: return abort(403) if app.config['no_files'] else send_file(requested, as_attachment=False) 
        else:
            global loaded_pages
            if clear and not showdlink: # clear before loading
                loaded_pages.clear()
                return redirect(url_for('route_home'))
            if (requested not in loaded_pages) or refresh: loaded_pages[requested] = nb2html(
                    requested, 
                    html_title=app.config['title'] if not showdlink else None, 
                    template_name=app.config['template'], 
                    no_script=False, 
                    favicon=True, 
                    tlink=app.config['ttext'], 
                    dlink=app.config['dtext'] if showdlink else None, 
                    hlink = app.config['htext'] if showdlink else None,
                    header = app.config['header'] if showdlink else None,
                    durl=f"{request.base_url}?{app.config['query_download']}", 
                    align='left')
                #with open('??.html','w') as f: f.write(loaded_pages[requested]) # save a copy to disk?
            if refresh: return redirect(url_for('route_home', query=query))
            else:
                if download: return send_file(requested, as_attachment=True) #<--- downloading ipynbs
                else: return  loaded_pages[requested]


#%% Server Section
def endpoints(athost):
    if athost=='0.0.0.0':
        ips=set()
        try:
            import socket
            for info in socket.getaddrinfo(socket.gethostname(), None):
                if (info[0].name == socket.AddressFamily.AF_INET.name): ips.add(info[4][0])
        except: pass
        ips=list(ips)
        ips.extend(['127.0.0.1', 'localhost'])
        return ips
    else: return [f'{athost}']

for endpoint in endpoints(parsed.host): sprint(f'◉ http://{endpoint}:{parsed.port}')
start_time = datetime.datetime.now()
sprint('◉ start server @ [{}]'.format(start_time))
serve(app,
    host = parsed.host,          
    port = parsed.port,          
    url_scheme = 'http',     
    threads = parsed.threads,    
    connection_limit = parsed.max_connect,
    max_request_body_size = str2bytes(parsed.max_size),
    _quiet=True,
)
end_time = datetime.datetime.now()
sprint('◉ stop server @ [{}]'.format(end_time))
sprint('◉ server up-time was [{}]'.format(end_time - start_time))

#%%

# author: Nelson.S
