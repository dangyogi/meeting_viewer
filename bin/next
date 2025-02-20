#!/usr/bin/python

import sys
from pathlib import Path
import os
import re
from itertools import filterfalse

Metadata = Path("metadata")
Motiondir = Path('.')

def meta(name):
    return Metadata / name

def get_current(err_no_current=True):
    r'''Returns current motion as Path.
    '''
    cur = meta('current')
    if cur.exists():
        return Path(cur.read_text().split()[0])
    if err_no_current:
        print("ERROR: no current file", file=sys.stderr)
        sys.exit(1)
    return None

def as_list(filename):
    r'''Returns the first word on each line of filename as a list.

    Lines starting with '#' are ignored.
    '''
    path = meta(filename)
    if not path.exists(): return []
    with path.open() as f:
        ans = [line.split()[0]
               for line in f
               if line[0] != '#']
        #print("as_list", filename, ans)
        return ans

def in_file(name, filename):
    r'''True if name is subordinate_to any motion in filename.

    Accepts Path as name.
    '''
    return in_list(name, as_list(filename))

def in_list(name, motions):
    r'''True if name is subordinate_to any motion in motions.

    Accepts Path as name.
    '''
    for motion in motions:
        if subordinate_to(name, motion):
            return True
    return False

def subordinate_to(a, b):
    r'''True if motion a is subordinate to motion b.

    For example, mot-1-1 and mot-1.1 are subordinate to mot, mot-1 and mot-1.2, but not mot-2.

    >>> subordinate_to('mot-1-1', 'mot')
    True
    >>> subordinate_to('mot-1-1', 'mot.2')
    True
    >>> subordinate_to('mot-1-1', 'mot.2.3')
    True
    >>> subordinate_to('mot-1-1', 'mot-1')
    True
    >>> subordinate_to('mot-1-1', 'mot-1.2')
    True
    >>> subordinate_to('mot-1-1', 'mot-1-1')
    True
    >>> subordinate_to('mot-1-1', 'mot-2')
    False
    >>> subordinate_to('mot-1.1', 'mot')
    True
    >>> subordinate_to('mot-1.1', 'mot.2')
    True
    >>> subordinate_to('mot-1.1', 'mot.2.3')
    True
    >>> subordinate_to('mot-1.1', 'mot-1')
    True
    >>> subordinate_to('mot-1.1', 'mot-1.2')
    True
    >>> subordinate_to('mot-1.1', 'mot-1-1')
    False
    >>> subordinate_to('mot-1.1', 'mot-2')
    False
    >>> subordinate_to('mot-1', 'mot')
    True
    >>> subordinate_to('mot-1', 'mot.2')
    True
    >>> subordinate_to('mot-1', 'mot.2.3')
    True
    >>> subordinate_to('mot-1', 'mot-1')
    True
    >>> subordinate_to('mot-1', 'mot-1.2')
    True
    >>> subordinate_to('mot-1', 'mot-1-1')
    False
    >>> subordinate_to('mot-1', 'mot-2')
    False
    >>> subordinate_to('mot.1', 'mot')
    True
    >>> subordinate_to('mot.1.2', 'mot')
    True
    >>> subordinate_to('mot.1', 'mot.2')
    True
    >>> subordinate_to('mot.1.2', 'mot.2')
    True
    >>> subordinate_to('mot.1', 'mot.2.3')
    True
    >>> subordinate_to('mot.1.2', 'mot.2.3')
    True
    >>> subordinate_to('mot.1', 'mot-1')
    False
    >>> subordinate_to('mot.1.1', 'mot-1')
    False
    >>> subordinate_to('mot.1', 'mot-1.2')
    False
    >>> subordinate_to('mot.1', 'mot-1-1')
    False
    >>> subordinate_to('mot.1', 'mot-2')
    False
    >>> subordinate_to('foo', 'foobar')
    False
    >>> subordinate_to('foobar', 'foo')
    False

    Accepts Path for a or b.
    '''
    a = str(a).split('.')[0]  # strip .X
    b = str(b).split('.')[0]  # strip .X
    return a == b or a.startswith(b + '-')

def check_open(motion):
    if in_file(motion, 'failed'):
        print(f"{motion} already failed", file=sys.stderr)
        sys.exit(1)
    if in_file(motion, 'passed'):
        print(f"{motion} already passed", file=sys.stderr)
        sys.exit(1)

def append(filename, motion, *reason):
    r'''Accepts Path as motion.
    '''
    with meta(filename).open('at') as f:
        if reason:
            print(str(motion), ' '.join(reason), file=f)
        else:
            print(str(motion), file=f)

def read(filename):
    with Path(filename).open() as f:
        return f.read()

number_re = re.compile(r'([-.][0-9]+)')

def expand(name):
    r'''Expands motion name into its parts for sorting.

    'motion-1.2' expands to ['motion', 1, '-', 2, '.'] so that numbers sort properly,
    also so that -2 and .2 sort together, for example to get motion-2, motion.2 and motion-3;
    rather than motion-2, motion-3, motion.2.

    Accepts Path as name.
    '''
    def parts():
        for part in number_re.split(str(name)):
            if part:
                if part[0] in '.-':
                    yield int(part[1:])
                    yield part[0]
                else:
                    yield part
    return tuple(parts())

def motion_history(motion, failed=()):
    r'''Shows the history of motion in chronological order.

    Prunes out failed motions.
    '''
    return [Path(motion)] + sorted(filterfalse(lambda path: in_list(path, failed),
                                               Motiondir.glob(motion + '[-.]*')),
                                   key=expand)

def cur_agenda():
    failed = frozenset(as_list('failed'))
    passed = frozenset(as_list('passed'))
    for motion in as_list('agenda'):
        #print("cur_agenda looking at motion", motion)
        if not in_list(motion, failed) and not in_list(motion, passed):
            history = motion_history(motion, failed)
            #print("cur_agenda", motion, "got history", history)
            yield history[-1]

def agenda():
    for motion in cur_agenda():
        print(motion)

def current(motion=None):
    r'''Displays or sets current motion.
    '''
    if motion is None:
        print(str(get_current(False)))
    else:
        meta('current').write_text(motion + '\n')

def passed():
    r'''Shows the list of main motions that have passed a vote.

    Amendments that have passed are not shown.
    '''
    with meta('passed').open() as f:
        print(f.read(), end='')

def failed():
    r'''Shows the list of all motions that have failed a vote.

    This includes amendments.
    '''
    with meta('failed').open() as f:
        print(f.read(), end='')

def start(_no_edit, motion=None):
    r'''touches motion and execs editor on it.

    If motion is omitted, the current motion is restarted.
    '''
    print("start", _no_edit, motion)
    if motion is None:
        motion_path = get_current()
        print("restarting", str(motion_path))
    else:
        motion_path = Path(motion)
        meta('current').write_text(str(motion).rstrip('\n') + '\n')
    #motion_path.touch()
    with motion_path.open('at'):
        pass
    if not _no_edit:
        editor = Path(os.environ['EDITOR'])
        os.execl(editor, editor.name, motion_path)

def next(_no_edit, _dry_run):
    for motion in cur_agenda():
        print("next is", str(motion))
        if _dry_run:
            return
        start(_no_edit, motion)
    print("The agenda is done!")

tail_re = re.compile(r'-[0-9]+(\.[0-9]+)*$')

def tail(motion):
    m = tail_re.search(str(motion))
    if m is None:
        return None
    return m.group()

def dot_tail(motion):
    m = tail_re.search(str(motion))
    if m is None:
        return None
    return m.group(1)

section_re = re.compile(r'^(-{3,})$', re.MULTILINE)

def sections(motion):
    data = read(motion)
    print("sections", section_re.search(data))
    return section_re.split(data)

#s/~~\(~\{0,1\}[^~]\)*~~//g
#del_re = re.compile(r'~~(?:~?[^~]+)*~~')
del_re = re.compile(r'~~.*?~~', re.DOTALL)

#s/\^\^\(\(\^\{0,1\}[^\^]\)*\)\^\^/\1/g
#ins_re = re.compile(r'\^\^(\^?[^\^]+)*\^\^')
ins_re = re.compile(r'\+\+(.*?)\+\+', re.DOTALL)

def pass_block(text):
    print("pass_block", text)
    no_del = del_re.sub('', text)
    print("no_del", no_del)
    ans = ins_re.sub(r'\1', no_del)
    #print("ins parts", parts)
    #ans = ''.join(parts)
    print("ans", ans)
    return ans

def pass_(_no_edit, _dry_run, reason_):
    motion = get_current()
    print("pass", str(motion), reason_)
    check_open(motion)
    hyphen_count = str(motion).count('-')
    if hyphen_count:
        t = tail(motion)
        assert t is not None and t[0] == '-'
        dot = Path(str(motion)[:-len(t)] + '.' + t[1:])
        print("pass: got amendment, creating", dot)
        if dot.exists():
            print(f"{str(motion)} already passed", file=sys.stderr)
            sys.exit(1)
        if _dry_run:
            dot = Path('tmp.' + str(dot))
        if hyphen_count == 1:
            secs = sections(motion)
            print("pass: primary amendment")
            print("secs", secs)
            assert len(secs) == 3
            with dot.open('wt') as f:
                f.write(pass_block(secs[0]))
        else:
            assert hyphen_count == 2
            secs = sections(motion)
            print("pass: secondary amendment")
            print("secs", secs)
            assert len(secs) == 5
            with dot.open('wt') as f:
                f.write(secs[0])
                f.write(secs[1])   # hyphens
                f.write(pass_block(secs[2]))
        print("pass created", str(dot))
        if not _dry_run:
            #append('passed', motion, *reason_)
            start(_no_edit, dot)
    else:
        print("pass: got motion, appending", str(motion), "to 'passed'")
        if not _dry_run:
            append('passed', motion, *reason_)
            #FIX: next(_no_edit)

def fail(_no_edit, _dry_run, reason_):
    motion = get_current()
    print("fail", str(motion), reason_)
    check_open(motion)
    if _dry_run:
        print("fail appending", str(motion), "to 'failed'")
    else:
        append('failed', motion, *reason_)
    last_hyphen = str(motion).rfind('-')
    if last_hyphen >= 0:
        parent = str(motion)[: last_hyphen]
        print("fail: got amendment, starting", parent)
        if not _dry_run:
            start(_no_edit, parent)
    else:
        print("fail: got motion")
        #FIX: next(_no_edit)

def amend(_no_edit, _dry_run):
    current_motion = get_current()
    motion = str(current_motion)

    # strip .X
    dot = motion.find('.')
    if dot >= 0:
        motion = motion[:dot]

    print("amend", motion)
    check_open(motion)
    hyphen_count = motion.count('-')
    if hyphen_count > 1:
        print(f"ERROR: amend {motion}, can't amend a secondary amendment", file=sys.stderr)
        sys.exit(1)
    if hyphen_count == 1:
        kind = 'amendment'
    else:
        kind = 'motion'
    next_num = max((int(str(name)[len(motion) + 1:].split('.')[0].split('-')[0])
                      for name in Motiondir.glob(motion + '[-.]*')),
                   default=0) + 1
    new_file = Path(motion + f"-{next_num}")
    print("amend, new_file", str(new_file))
    if _dry_run:
        new_file = Path('tmp.' + str(new_file))
    with new_file.open('wt') as f:
        with current_motion.open() as old_f:
            f.write(old_f.read())
        print("-------------------", file=f)
        print(f"amend the {kind} by ", file=f)
    print("amend created", str(new_file))
    if not _dry_run:
        start(_no_edit, new_file)

def new(_no_edit, _dry_run):
    # filenames are: newN
    last_num = max([int(str(name)[3:]) for name in Motiondir.glob('new*')], default=0)
    new_file = Path(f"new{last_num + 1}")
    print("new", str(new_file))
    if not _dry_run:
        start(_no_edit, new_file)

def commands():
    def get_args(fn):
        ans = []
        for arg, kind in getargs(fn):
            if kind == 'option':
                ans.append(f" [{arg[1:3]}|{arg}]")
            elif kind == 'required':
                ans.append(' ' + arg)
            elif kind == 'list':
                ans.append(' ' + arg + '...')
            else:
                ans.append(f" [{arg}]")
        return ''.join(ans)
    for name, fn in sorted(Commands.items()):
        print(f"{name}{get_args(fn)}")
        doc = inspect.getdoc(fn)
        if doc is not None:
            for line in doc.rstrip('\n ').split('\n'):
                print('    ', line, sep='')
        print()

Commands = {
    "current": current,
    "agenda": agenda,
    "passed": passed,
    "failed": failed,
    "start": start,
    "next": next,
    "pass": pass_,
    "fail": fail,
    "amend": amend,
    "new": new,
    "commands": commands,
}

def getargs(fn):
    r'''Yields arg, kind.

    Where kind is 'option', 'required', 'list' or a default value

    If arg starts with '_', all '_' have been replaced with '-', leaving the initial '-'.
    '''
    argspec = inspect.getfullargspec(fn)
    fn_args = argspec.args
    fn_defaults = argspec.defaults or ()
    num_no_defaults = len(fn_args) - len(fn_defaults)
    arg_translate = {}
    for arg in fn_args[: num_no_defaults]:
        if arg[0] == '_':
            yield '-' + arg.replace('_', '-'), 'option'
        elif arg[-1] == '_':
            yield arg, 'list'
        else:
            yield arg, 'required'
    for arg, default in zip(fn_args[num_no_defaults:], fn_defaults):
        yield arg, default


if __name__ == "__main__":
    import argparse
    import inspect

    name = Path(sys.argv[0]).name
    fn = Commands[name]
    doc = inspect.getdoc(fn)
    if doc is None:
        parser = argparse.ArgumentParser()
    else:
        parser = argparse.ArgumentParser(description=doc.rstrip('\n '))
    arg_translate = {}
    for arg, kind in getargs(fn):
        if kind == 'option':
            #parser.add_argument(arg, arg[1:3], default=False, action='store_true')
            parser.add_argument(arg[1:3], arg, default=False, action='store_true')
            arg = arg.replace('-', '_')
            arg_translate[arg[2:]] = arg[1:]
        elif kind == 'required':
            parser.add_argument(arg)
        elif kind == 'list':
            parser.add_argument(arg, nargs='*')
        else:
            parser.add_argument(arg, nargs='?', default=kind)

    args = parser.parse_args()
    #print("args", args)

    #print("vars(args)", vars(args))
    #print("arg_translate", arg_translate)
    arg_dict = {arg_translate.get(name, name): value for name, value in vars(args).items()}
    #print("arg_dict", arg_dict)
    fn(**arg_dict)
