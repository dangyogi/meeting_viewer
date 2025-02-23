# async_test.py

import asyncio

async def foo(x):
    print("foo", x, "called")
    await asyncio.sleep(x)
    print("foo", x, "done")

background_tasks = set()

def add_task(cor):
    global background_tasks
    task = asyncio.create_task(cor)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

async def start():
    for i in range(4):
        add_task(foo(3 - i))

async def long_wait(t, cor):
    print("long_wait creating task")
    task = asyncio.create_task(cor)
    print("long_wait created task")
    await asyncio.sleep(t)


print("calling run")
asyncio.run(long_wait(10, start()))
print("run done")
