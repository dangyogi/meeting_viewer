# tester.py

import asyncio
import os.path
from pathlib import Path
import time
import argparse

from aiohttp import web
import aionotify
from aiohttp_sse import sse_response
import markdown
from markdown.inlinepatterns import SimpleTextInlineProcessor
from markdown.extensions import Extension


#class SaveUnderline(SimpleTextInlineProcessor):
#    def getCompiledRegExp(self):
#        print("SaveUnderline.getCompiledRegExp")
#        #raise AssertionError
#        return super().getCompiledRegExp()
#
#    def handleMatch(self, m, data):
#        print("SaveUnderline.handleMatch", m, data)
#        return super().handleMatch(m, data)

class UnderlineExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(SimpleTextInlineProcessor(NOT_STRONG_RE, md),
                                   #SaveUnderline(NOT_STRONG_RE, md),
                                   'underline', 75)

NOT_STRONG_RE = r'(_{4,})'
#NOT_STRONG_RE = r'((\*{4,}|_{4,}))'
#NOT_STRONG_RE = r'((\*{4,}|_{4,}))'
#NOT_STRONG_RE = r'((^|(?<=\s))(\*{4,}|_{4,})(?=\s|$))'
#NOT_STRONG_RE = r'((^|(?<=\s))(\*{1,}|_{1,})(?=\s|$))'

md = markdown.Markdown(extensions=[
  # no list extension     # must indent nested lists more than text
  #'sane_lists',          # included in markdown package
                         # must indent nested lists more than text, no blank lines needed
  'mdx_truly_sane_lists', # pip install mdx_truly_sane_lists, indent nested lists less than text

  #'prependnewline',      # pip install prependnewline, indent nested lists more than text
  #'mdx_breakless_lists',  # pip install mdx-breakless-lists, indent nested lists more than text

  'citeurl',              # pip install citeurl
  #'pymdownx.escapeall',  # what do I have to install for this to work?
  'markdown_del_ins',     # pip install markdown-del-ins ~~del~~ ++ins++
  UnderlineExtension(),   # override _italics_ and __bold__ to leave 4 or more _ unmolested.
])

class MultiQueue:
    r'''Cross coroutine queue that feeds several clients.  Each "push" is sent to all clients (as they
        "pop").  Each client is identified by a unique key that they create.  Clients must register and
        unregister their key.
    '''
    def __init__(self):
        self.next_event = asyncio.Event()
        self.registered_keys = set()
        self.started_keys = set()         # keys that have received the last push
        self.push_lock = asyncio.Lock()   # released when all pop threads have receved the last push
        self.pop_event = asyncio.Event()  # set when all pop threads have received the last push
        self.pop_event.set()

    def empty(self):
        return not self.registered_keys

    def register(self, key):
        assert key not in self.registered_keys
        self.registered_keys.add(key)
        print("MultiQueue.register", key, "gives", self.registered_keys)

    def unregister(self, key):
        self.registered_keys.remove(key)
        print("MultiQueue.unregister", key, "leaves", self.registered_keys)
        if key in self.started_keys:
            self.started_keys.remove(key)

    async def push(self, filename, data):
        print("push", filename, "waiting for push_lock")
        await self.push_lock.acquire()
        print("push", filename, "got push_lock")
        self.started_keys = set()
        self.data = data
        self.pop_event.clear()
        self.next_event.set()   # signal pop threads

    async def pop(self, key):
        assert key in self.registered_keys
        while True:
            print("pop", key, "waiting for next_event, started_keys", self.started_keys)
            await self.next_event.wait()
            print("pop", key, "got next_event")
            if key not in self.started_keys:
                print("pop", key, "returning new data!")
                self.started_keys.add(key)
                return self.data
            # else key in started_keys, has already processed last push
            print("pop", key, "already processed last push, started_keys", self.started_keys,
                  "registered_keys", self.registered_keys)
            if self.registered_keys <= self.started_keys:
                # all pop threads have received their data
                print("pop", key, "all pop threads have received their data")
                self.next_event.clear()     # stop triggering other pop threads
                self.push_lock.release()    # unlock next push
                self.pop_event.set()
            else:
                # wait for all pop threads to receive the last push
                print("pop", key, "waiting for all pop threads to receive the last push")
                await self.pop_event.wait()


def convert(filename):
    r'''Convert the markdown contents of filename to html and return it.
    '''
    print("converting", filename, "from markdown to html")
    new_path = os.path.join(Watch_dir, filename)
    with open(new_path, 'rt') as file:
        return md.convert(file.read())

async def watcher(app):
    r'''Coroutine to listen for changes to Watch_dir and post html to app['multi_queue'].

    As the changes come in, this converts the files from markdown to html and pushes the html to the
    MultiQueue stored in app['multi_queue'].
    '''
    watcher = aionotify.Watcher()
    watcher.watch(alias='watch_dir', path=Watch_dir,
                  flags=aionotify.Flags.CLOSE_WRITE ) # | aionotify.Flags.MODIFY)
    await watcher.setup()
    print("watcher started")
    try:
        while True:
            event = await watcher.get_event()
            if event.name[0] != '.' and not event.name.isdigit():
                if not app['multi_queue'].empty():
                    print("watcher got", event.name, "with registered clients")
                    new_filename = event.name
                    new_contents = convert(new_filename)
                    print("watcher", event.name, "pushing contents")
                    await app['multi_queue'].push(new_filename, new_contents)
                    print("watcher", event.name, "push done")
                else:
                    print("watcher got", event.name, "no registered clients")
    finally:
        print("watcher done")
        watcher.close()

async def start_background_tasks(app):
    r'''Run by aiohttp.Application before starting the run_app task.
    '''
    print("start_background_tasks")
    app['multi_queue'] = MultiQueue()

    # The watcher will run concurrently with the web server coroutine.
    app['watcher'] = asyncio.create_task(watcher(app))

    print("start_background_tasks done")

async def cleanup_background_tasks(app):
    r'''Run by aiohttp.Application after terminating the run_app task.
    '''
    print("cleanup_background_tasks")
    app['watcher'].cancel()  # kill watcher task
    await app['watcher']
    print("cleanup_background_tasks done")

async def init(request):
    r'''Handles request to '/'.

    Just sends static/start.hml.
    '''
    print("init called")
    return web.FileResponse(path="static/start.html")

async def static(request):
    r'''Handles requests to '/static/*'.

    Just sends the file in the source code's static directory.
    '''
    path = os.path.join('static', request.match_info['filename'])
    print("static called with filename", request.match_info['filename'], "path", path)
    return web.FileResponse(path=path)

Viewer_num = 1

async def viewer(request: web.Request) -> web.StreamResponse:
    r'''Handles requests to '/viewer' for server-sent events.

    Each event is simply the html contents of the file that just changed.
    '''
    global Viewer_num
    client_ip = request.remote
    viewer_num = Viewer_num
    Viewer_num += 1
    print("viewer", viewer_num, "called from", client_ip)
    async with sse_response(request) as resp:
        pick_file = None
        pick_time = time.time() - 3600
        #print("pick_time", pick_time)
        for path in Path(Watch_dir).iterdir():
            if path.is_file() and path.name[0] != '.' and not path.name.isdigit():
                mtime = path.stat().st_mtime
                #print(path, "st_mtime", mtime, "delta", time.time() - mtime)
                if mtime >= pick_time:
                    pick_file = path.name
                    pick_time = mtime
        print("lastest file", pick_file)
        contents = pick_file and convert(pick_file)
        app['multi_queue'].register(viewer_num)
        try:
            while resp.is_connected():
                if contents is None:
                    contents = await app['multi_queue'].pop(viewer_num)
                if resp.is_connected():
                    print("viewer", viewer_num, "got contents", contents[:contents.find('\n')], "...")
                    await resp.send(contents)
                    contents = None
        finally:
            app['multi_queue'].unregister(viewer_num)
    print("viewer", viewer_num, "done")
    return resp  # ??


# Get the show on the road!

print("__file__", __file__)
Source_dir = os.path.dirname(__file__)
print("Source_dir", Source_dir)

#print("md.convert('hello ~~old~~ and ++new++ stuff')", md.convert('hello ~~old~~ and ++new++ stuff'))

app = web.Application()
app.add_routes([
  web.get('/static/{filename}', static),
  web.get('/viewer', viewer, allow_head=False),
  web.get('/', init),
])

parser = argparse.ArgumentParser(description="web server to share words in meetings")
parser.add_argument('watch_dir', nargs='?', default='testmeeting',
                    help='shares all changes in this directory')
args = parser.parse_args()

Watch_dir = args.watch_dir

app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

web.run_app(app)
