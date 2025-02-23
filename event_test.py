# event_test.py

import asyncio

Data = None

Events = {}  # id: Event

async def watcher():
    global Data
    for i in range(10):
        Data = i
        print("watcher got", i, "with", len(Events), "clients")
        for e in Events.values():
            e.set()
        await asyncio.sleep(1)

async def viewer(i):
    global Events
    Events[i] = my_event = asyncio.Event()
    while True:
        await my_event.wait()
        print("viewer", i, "got", Data)
        my_event.clear()
        await asyncio.sleep(i)

Tasks = []

async def run():
    global Tasks
    for i in range(1, 4):
        Tasks.append(asyncio.create_task(viewer(i)))
    await watcher()

asyncio.run(run())
