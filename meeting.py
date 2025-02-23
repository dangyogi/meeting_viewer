# meeting.py

import sys
import asyncio
import os.path
import tempfile
from pathlib import Path
import argparse

from aiohttp import web
from aiohttp_sse import sse_response


# Logging:

class SplitOutput:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def close(self):
        self.a.close()
        self.b.close()

    def flush(self):
        self.a.flush()
        self.b.flush()

    def seekable(self):
        return False

    def readable(self):
        return False

    def writable(self):
        return True

    def write(self, data):
        self.a.write(data)
        self.b.write(data)


def open_log(quiet):
    global Log_filename, Log_file
    prefix = 'monitor-'
    log_fileno, Log_filename = tempfile.mkstemp(prefix=prefix, suffix=".txt", text=True)

    # Remove old log files
    tmpdir = Path(os.path.dirname(Log_filename))
    for file in tmpdir.glob(prefix + '*'):
        if str(file) != Log_filename:
            #print("log glob got", repr(file))
            file.unlink()

    Log_file = open(log_fileno, 'w+t', buffering=1)  # line buffering

    if quiet:
        sys.stderr = Log_file
        sys.stdout = Log_file
    else:
        split_output = SplitOutput(sys.stdout, Log_file)
        sys.stderr = split_output
        sys.stdout = split_output

    log("Log_filename", repr(Log_filename))

def log(*args):
    print(*args)
    #print(*args, file=Log_file)


# Web pages:

async def init(request):
    r'''Handles request to '/'.

    Just sends static/signin.hml.
    '''
    log("init called")
    return web.FileResponse(path="static/signin.html")

async def start(request):
    r'''Handles request to '/start'.

    Just sends static/start.hml.
    '''
    log("start called for", request.query['fname'])
    return web.FileResponse(path="static/start.html")

async def static(request):
    r'''Handles requests to '/static/*'.

    Just sends the file in the source code's static directory.
    '''
    path = os.path.join(Source_dir, 'static', request.match_info['filename'])
    log("static called with filename", request.match_info['filename'], "path", path)
    return web.FileResponse(path=path)


Viewer_num = 1

async def viewer(request: web.Request) -> web.StreamResponse:
    r'''Handles requests to '/viewer' for server-sent events.

    Each event is simply the html contents of the file that just changed.
    '''
    global Viewer_num
    client_ip = request.remote
    fname = request.query['fname']
    viewer_num = fname, Viewer_num
    Viewer_num += 1
    log("viewer", viewer_num, "called from", client_ip)
    app = request.app
    async with sse_response(request) as resp:
        contents = getattr(app['globals'], 'new_contents', None)

        # set up my_event
        my_event = asyncio.Event()
        app['events'][viewer_num] = my_event
        try:
            while resp.is_connected():
                if contents is None:  # False the first time through if initial file found
                    await my_event.wait()
                    contents = app['globals'].new_contents
                    my_event.clear()
                if resp.is_connected():
                    log("viewer", viewer_num, "got contents", contents[:contents.find('\n')], "...")
                    await resp.send(contents)
                    contents = None
        finally:
            del app['events'][viewer_num]
    log("viewer", viewer_num, "done")
    return resp  # ??


async def change(request):
    r'''Called on 'put' to /change

    Body of request is html to post to all clients.
    '''
    filename = request.query['filename']
    log()
    log("change called for", filename)
    app = request.app
    if request.headers['Authorization'] != app['auth']:
        print("change: unauthorized request, got", request.headers['Authorization'],
              "expected", app['auth'])
        return web.HTTPUnauthorized()
    assert request.content_type.startswith('text/html:'), f"got content-type {request.content_type}"
    #assert request.body_exists
    #assert request.can_read_body
    contents = await request.text()
    if contents:
        app['globals'].new_filename = filename
        app['globals'].new_contents = contents
        log("change pushing", contents[:contents.find('\n')], "... to",
            len(app['events']), "clients")
        for ev in app['events'].values():
            ev.set()
        #await app['multi_queue'].push(new_filename, new_contents)
        log("change", filename, "sets done")
    elif filename == 'log':
        log("change", filename, "returning log file!")
        return await get_log(request)
    else:
        log("change", filename, "empty, not sent to clients")
        log()
        log("MARK", filename)
    return web.Response()


async def get_log(request):
    r'''Returns current log file contents as download file.
    '''
    log()
    log("log called")
    app = request.app
    #if request.headers['Authorization'] != app['auth']:
    #    print("change: unauthorized request, got", request.headers['Authorization'],
    #          "expected", app['auth'])
    #    return web.HTTPUnauthorized()
    Log_file.seek(0)
    text = Log_file.read()
    filename = os.path.basename(Log_filename)
    return web.Response(headers={'Content-Disposition': f'attachment; filename={filename}'},
                        #text=text.encode('utf-8'))
                        text=text)


# Get the show on the road!

parser = argparse.ArgumentParser(description="meeting monitor")
parser.add_argument('--quiet', '-q', default=False, action='store_true')
parser.add_argument('auth')
args = parser.parse_args()

open_log(args.quiet)

log("__file__", __file__)
Source_dir = os.path.dirname(__file__)
log("Source_dir", Source_dir)

app = web.Application()
app.add_routes([
  web.get('/', init),
  web.get('/start', start),
  web.get('/viewer', viewer, allow_head=False),
  web.get('/static/{filename}', static),
  web.put('/change', change),
  web.get('/log', get_log, allow_head=False),
])

class Globals:
    r'''Just a place to store attributes...

    An instance of Globals is stored in app['globals'].
    '''
    pass

app['auth'] = args.auth
app['events'] = {}
app['globals'] = Globals()

web.run_app(app)
