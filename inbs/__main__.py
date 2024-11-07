#-----------------------------------------------------------------------------------------
from sys import exit
if __name__!='__main__': exit(f'[!] can not import {__name__}.{__file__}')
#-----------------------------------------------------------------------------------------

#%% Global

import os, argparse, datetime, logging
parser = argparse.ArgumentParser()
parser.add_argument('--base',           type=str, default='',                     help="path to base dir"     )
parser.add_argument('--template',       type=str, default='lab',                  help="classic/lab/reveal"   )
parser.add_argument('--title',          type=str, default='',                     help="to be used when empty title is found"   )
parser.add_argument('--home',           type=str, default='',                     help="home page"   )

parser.add_argument('--query_refresh',  type=str, default='!',              help="[-] # refresh ?!"         )
parser.add_argument('--query_download', type=str, default='?',              help="[-] # download ??"        )
parser.add_argument('--no_script',      type=int, default=1,                help="[-] if true, remove any embedded <script> tags")
parser.add_argument('--dlink',          type=int, default=1,                help="if true, shows a download link on each page except home page")
parser.add_argument('--dtext',          type=str, default='📥️',               help="text for download link"   )
parser.add_argument('--dalign',          type=str, default='',               help="align for download link"   )
parser.add_argument('--dafter',          type=int, default=0,                help="if true, shows download link after header")
parser.add_argument('--tlink',           type=int, default=1,                help="if true, shows a top link on each page")
parser.add_argument('--ttext',           type=str, default='🔝',               help="text for top link"   )
parser.add_argument('--talign',          type=str, default='left',               help="align for top link"   )

parser.add_argument('--ext',            type=str, default='.ipynb',         help="[-] extension for notebook files - case sensetive")
parser.add_argument('--log',            type=str, default='',               help="log file name - keep empty for no logging")

parser.add_argument('--host',           type=str, default='0.0.0.0',                                    )
parser.add_argument('--port',           type=str, default='8888',                                       )
parser.add_argument('--threads',        type=int, default=10,                                           )
parser.add_argument('--max_connect',    type=int, default=500,                                          )
parser.add_argument('--max_size',       type=str, default='1024MB',          help="size of http body"   )




parsed = parser.parse_args()

BASE = os.path.abspath(parsed.base)
if not os.path.isdir(BASE): exit(f'No directory found at {BASE}')


# ------------------------------------------------------------------------------------------
LOGFILE = f'{parsed.log}'
if LOGFILE: 
# ------------------------------------------------------------------------------------------
    try:
        # Set up logging to a file
        logging.basicConfig(filename=LOGFILE, filemode='a', level=logging.INFO, format='%(asctime)s - %(message)s')
        # also output to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(console_handler)
    except: exit(f'[!] Logging could not be setup at {LOGFILE}')
    def sprint(msg): logging.info(msg) 
# ------------------------------------------------------------------------------------------
else:
    def sprint(msg): print(msg) 
# ------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------
#%% Definitions

# import packages after all exit statements
from nbconvert import HTMLExporter 
from flask import Flask, request, abort, redirect, url_for, send_file
from waitress import serve

str2bytes_sizes = dict(BB=2**0, KB=2**10, MB=2**20, GB=2**30, TB=2**40)
def str2bytes(size): return int(float(size[:-2])*str2bytes_sizes.get(size[-2:].upper(), 0))

def remove_tag(page, tag): # does not work on nested tags
    fstart, fstop = f'<{tag}', f'/{tag}>'
    while True:
        istart = page.find(fstart)
        if istart<0: break
        istop = page[istart:].find(fstop)
        page = f'{page[:istart]}{page[istart+istop+len(fstop):]}'
    return page


STYLE_CSS = """<style type="text/css">

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
</style>
"""
def nb2html(source_notebook, template_name, no_script, html_title=None, parsed_title=None, dlink='', dtext='', dalign='', tlink='', ttext='', talign=''):
    if html_title is None: # auto infer
        html_title = os.path.basename(source_notebook)
        iht = html_title.rfind('.')
        if not iht<0: html_title = html_title[:iht]
        if not html_title: html_title = (parsed_title if parsed_title else os.path.basename(os.path.dirname(source_notebook)))
    try:    
        page, _ = HTMLExporter(template_name=template_name).from_file(source_notebook,  dict(  metadata = dict( name = f'{html_title}' )    )) 
        if no_script: page = remove_tag(page, 'script') # force removing any scripts
    except: page = None

    if dlink or tlink:
        fstart = f'<body'
        istart = page.find(fstart)
        if istart<0: return None
        page = f'{page[:istart]}{STYLE_CSS}{page[istart:]}'
    
        if dlink:
            fstart, fstop = f'<body', f'>'
            istart = page.find(fstart)
            if istart<0: return None
            html_path = os.path.relpath(source_notebook, app.config['base'])
            istop = page[istart:].find(fstop)
            if app.config['dafter']:
                ins = f'<div align="{dalign}"><span class="btn_header">{html_title} @ ./{html_path}</span><a class="btn_actions" href="{dlink}?{app.config["query_download"]}">{dtext}</a></div><br><hr>'
            else:
                ins = f'<div align="{dalign}"><a class="btn_actions" href="{dlink}?{app.config["query_download"]}">{dtext}</a><span class="btn_header">{html_title} @ ./{html_path}</span></div><br><hr>'
            page = f'{page[:istart+istop+len(fstop)]}{ins}{page[istart+istop+len(fstop):]}'
        if tlink:
            fstart = f'</body'
            istart = page.find(fstart)
            if istart<0: return None
            ins= f'<hr><br><div align="{talign}"><a class="btn_actions" href="{tlink}">{ttext}</a></div>'
            page = f'{page[:istart]}{ins}{page[istart:]}'


    return  page


#%% App Setup 

sprint(f'⇒ Serving from directory {BASE}')

app = Flask(__name__)
app.config['base'] = BASE
app.config['template'] = parsed.template
app.config['dlink'] = bool(parsed.dlink)
app.config['dtext'] = parsed.dtext
app.config['dafter'] = parsed.dafter
app.config['dalign'] = parsed.dalign
app.config['tlink'] = bool(parsed.tlink)
app.config['ttext'] = parsed.ttext
app.config['talign'] = parsed.talign

app.config['home'] = f'{parsed.home}{parsed.ext}'
app.config['title'] = parsed.title
app.config['ext'] = parsed.ext # this is case sensetive
app.config['query_refresh'] = parsed.query_refresh 
app.config['query_download'] = parsed.query_download 
app.config['no_script'] = bool(parsed.no_script)
#app.config['cached'] = cached
loaded_pages = dict()
#print(app.config)

#%% Routes Section

@app.route('/', methods =['GET'], defaults={'query': ''})
@app.route('/<path:query>')
def route_home(query):
    
    refresh = app.config['query_refresh'] in request.args
    download = app.config['query_download'] in request.args
    base, ext, home = app.config['base'], app.config['ext'], app.config['home']
    tosend = False
    
    if ('.' in os.path.basename(query)):    tosend = (not query.lower().endswith(ext))
    else:                                   query += ext #---> auto add extension
    if ext==query: 			    query=home
    showdlink = not((query==home) or (query==ext))
    sprint (f'{"🔸" if showdlink else "🔹"} {request.remote_addr} [{request.method}] {request.url}')

    requested = os.path.join(base, query) # Joining the base and the requested path
    if not ((os.path.isfile(requested)) and (not os.path.relpath(requested, base).startswith(base))): return abort(404)
    else:
        if tosend: return send_file(requested, as_attachment=False)
        else:
            global loaded_pages
            if (requested not in loaded_pages) or refresh: 
                loaded_pages[requested] = nb2html(
                    requested, app.config['template'], 
                    app.config['no_script'],  
                    html_title=None, 
                    parsed_title=app.config['title'], 
                    dlink=((f'{request.base_url}' if app.config['dlink'] else '') if (showdlink) else ''), 
                    dtext=app.config['dtext'], 
                    dalign=app.config['dalign'],
                    tlink=((f'#' if app.config['tlink'] else '') if (app.config['tlink']) else ''), 
                    ttext=app.config['ttext'], 
                    talign=app.config['talign'],
                    )
            return redirect(url_for('route_home', query=query)) if refresh else ( send_file(requested, as_attachment=True) if download else loaded_pages[requested])
            # send_file(abs_path, as_attachment=("get" in request.args))
#%% Server Section
def endpoints(athost):
    if athost=='0.0.0.0':
        import socket
        ips=set()
        for info in socket.getaddrinfo(socket.gethostname(), None):
            if (info[0].name == socket.AddressFamily.AF_INET.name): ips.add(info[4][0])
        ips=list(ips)
        ips.extend(['127.0.0.1', 'localhost'])
        return ips
    else: return [f'{athost}']

start_time = datetime.datetime.now()
sprint('◉ start server @ [{}]'.format(start_time))
for endpoint in endpoints(parsed.host): sprint(f'◉ http://{endpoint}:{parsed.port}')
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
