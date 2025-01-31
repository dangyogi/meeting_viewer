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


# Markdown extensions for ~~deleted text~~ and ^^inserted text^^, these translate to <del> and <ins>
# html tags, respectively.

class DelExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(markdown.inlinepatterns.SimpleTagInlineProcessor(r'(~~)(.*?)(~~)',
                                                                                    'del'),
                                  'del', 105)

class InsExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(markdown.inlinepatterns.SimpleTagInlineProcessor(r'(\^\^)(.*?)(\^\^)',
                                                                                    'ins'),
                                  'ins', 106)

md = markdown.Markdown(extensions=[DelExtension(), InsExtension()])

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
        print("MultiQueue.register", key)
        self.registered_keys.add(key)

    def unregister(self, key):
        print("MultiQueue.unregister", key)
        self.registered_keys.remove(key)
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
                print("watcher got", event.name)
                if not app['multi_queue'].empty():
                    new_filename = event.name
                    new_contents = convert(new_filename)
                    print("watcher", event.name, "pushing contents")
                    await app['multi_queue'].push(new_filename, new_contents)
                    print("watcher", event.name, "push done")
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
    print("static called")
    path = os.path.join('static', request.match_info['filename'])
    print("static called with request.path", request.path, "filename", request.match_info['filename'],
          "path", path)
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
    print("viewer called from", client_ip, "viewer_num", viewer_num)
    async with sse_response(request) as resp:
        pick_file = None
        pick_time = time.time() - 3600
        print("pick_time", pick_time)
        for path in Path(Watch_dir).iterdir():
            if path.is_file() and path.name[0] != '.' and not path.name.isdigit():
                mtime = path.stat().st_mtime
                print(path, "st_mtime", mtime, "delta", time.time() - mtime)
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
                    print("viewer got contents, len", len(contents))
                    await resp.send(contents)
                    contents = None
        finally:
            app['multi_queue'].unregister(viewer_num)
    print("viewer done")
    return resp  # ??


# Get the show on the road!

print("__file__", __file__)

app = web.Application()
app.add_routes([
  web.get('/static/{filename}', static),
  web.get('/viewer', viewer, allow_head=False),
  web.get('/', init),
])

parser = argparse.ArgumentParser(description="web server to share words in meetings")
parser.add_argument('watch_dir', default='testmeeting', help='shares all changes in this directory')
args = parser.parse_args()

Watch_dir = args.watch_dir

app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

web.run_app(app)
