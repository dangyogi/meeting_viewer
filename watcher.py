# watcher.py

import os.path
import argparse

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import requests
import markdown
from markdown.inlinepatterns import SimpleTextInlineProcessor
from markdown.extensions import Extension


# Markdown Setup:

class UnderlineExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(SimpleTextInlineProcessor(NOT_STRONG_RE, md),
                                   'underline', 75)

NOT_STRONG_RE = r'(_{4,})'

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

def convert(new_path):
    r'''Convert the markdown contents of new_path to html and return it.
    '''
    #log("converting", filename, "from markdown to html")
    with open(new_path, 'rt') as file: 
        return md.convert(file.read())


def gen_auth():
    return event_handler.auth


class Event_handler(FileSystemEventHandler):
    def __init__(self, auth, watch_dir, url):
        super().__init__()
        self.auth = auth
        self.watch_dir = watch_dir
        self.url = url
        self.ignore = None

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent):
            src_path = event.src_path
            filename = os.path.basename(src_path)
            if filename[0] != '.' and not filename.isdigit() and filename != 'metadata' \
               and filename != self.ignore:
                print()
                print("on_modified got", filename)
                contents = convert(src_path)
                self.post(filename, contents)
                if contents:
                    print("watcher sent", contents[:contents.find('\n')], "...")
                else:
                    print("watcher sent empty file")

    def post(self, filename, content):
        r = requests.put(self.url,
                         params={'filename': filename},
                         headers={'content-type': 'text/html: charset=utf-8',
                                  'Authorization': gen_auth(),
                                 },
                         data=content.encode('utf-8'))
        print("post sent headers", r.request.headers)
        print("post got status", r.status_code, r.reason)
        print("post got headers", r.headers)
        if r.status_code == 200:
            if int(r.headers['content-length']):
                assert not content and filename == 'log'
                disp = r.headers['content-disposition']
                start = 'attachment; filename='
                assert disp.startswith(start)
                filename = disp[len(start):]
                path = os.path.join(self.watch_dir, filename)
                print("post saving log file as", path)
                with open(path, 'wt') as log_file:
                    self.ignore = filename
                    log_file.write(r.text)
        else: # got error from server
            if int(r.headers['content-length']):
                print("post got text", r.text)


def watcher(auth, watch_dir, url):
    r'''listens for changes to watch_dir and posts html to app['events'].

    As the changes come in, this converts the files from markdown to html and pushes the html to each
    Queue in app['events'].values().
    '''
    global event_handler
    print("watcher auth", auth, "watching", watch_dir, "posting to", url)
    observer = Observer()
    event_handler = Event_handler(auth, watch_dir, url)
    observer.schedule(event_handler, watch_dir, recursive=False)
    try:
        observer.start()
        observer.join()
    finally:
        print("capturing log file")
        event_handler.post('log', '')
        print("watcher thread terminated")
    #try:
    #    while observer.is_alive():
    #        print("observer.isAlive(), doing join")
    #        observer.join(1)
    #        print("observer.join(1) finished")
    #finally:
    #    print("terminating observer")
    #    observer.stop()
    #    observer.join()


#print("md.convert('hello ~~old~~ and ++new++ stuff')", md.convert('hello ~~old~~ and ++new++ stuff'))

parser = argparse.ArgumentParser(description="watcher to post file changes to meeting monitor")
parser.add_argument('auth', help='must provide same auth key to meeting.py!')
parser.add_argument('watch_dir', help='posts all changes in this directory')
parser.add_argument('url', nargs='?', default='http://70.126.41.242:8080/change',
                    help='url to post change to')
args = parser.parse_args()

watcher(args.auth, args.watch_dir, args.url)
