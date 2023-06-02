import logging
logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8', level=logging.DEBUG)
#import threading
from midi_integration import MidiIntegration
import logging
import time
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from pipewire import PipewireService
from pprint import pprint
from linker import Linker



logging.info("starting up")
modules = dict()

def make_stream():
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    def callback(message):
        loop.call_soon_threadsafe(queue.put_nowait, message)
    async def stream():
        while True:
            yield await queue.get()
    return callback, stream()

async def event_processor(stream):
  async for event in stream:
    if isinstance(event,list):
      for item in event:
          process_event(item)
    else:
      process_event(event)

def process_event(event):
    if event['source'] != "linker":
      asyncio.create_task(modules['linker'].receive_message(event))
    if event.get('destination','notexist') in modules.keys():
      asyncio.create_task(modules[event['destination']].receive_message(event))
      
    

def midi(c):
  for msg in c.get_input():
    pprint(msg)

async def main():
  global modules
  config =dict()
  with open("volume.yaml", "r") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        logging.error(exc)
  loops_brother = asyncio.get_event_loop()
  scheduler = AsyncIOScheduler()
  logging.debug("Running main loop")
  # This is where update tasks go.
  callback, stream = make_stream()
  if config.get('pipewire') is not None:
    devicemap = config['pipewire'].get('devices',dict())
    modules['pipewire'] = PipewireService(devicemap,callback=callback)
    asyncio.create_task(modules['pipewire'].realtime_start())
  #integration = MidiIntegration(config),callback=callback)
  modules['midi'] = MidiIntegration(config['controller'],callback=callback)
  modules['linker'] = Linker(config,callback)
  #scheduler.add_job(await event_processor(stream), 'interval', seconds=1)
  #scheduler.add_job(midi(controller), 'interval', seconds=1)
  asyncio.create_task(event_processor(stream))
  #scheduler.start()
  #asyncio.run(event_processor(stream))
  #await event_processor(stream)
  while True:
    await asyncio.sleep(1)
asyncio.run(main())
