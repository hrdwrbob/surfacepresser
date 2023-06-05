#!/usr/bin/env python3
import logging
logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8', level=logging.DEBUG)
#import threading
from midi_integration import MidiIntegration
import logging
import yaml
from midi_controller import MidiController
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from pipewire import PipewireService
from pprint import pprint
from linker import Linker
import argparse
import os



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
      
    

def get_yaml(path):
  if not os.path.isfile(path):
     logging.fatal("Could not find config file " + path)
     return None
  myyaml = dict()
  with open(path, "r") as stream:
    try:
        myyaml = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        logging.fatal(exc)  
        exit()
  dir = os.path.dirname(path)
  for include in myyaml.get('includes',list()):
     file = os.path.join(dir,get_yaml(include))
     myyaml.update(file)
  return myyaml

async def main():
  global modules
  
  parser = argparse.ArgumentParser(description='Surface Presser - Midi controller interface.')
  parser.add_argument('--config',nargs='*',default=['surfacepresser.yaml'],
                      help='yaml config files')
  parser.add_argument('--miditest', nargs='?',metavar='MIDI Controller',
                      help='test mode - show midi commands only')
  parser.add_argument('--midilist',action='store_true',
                      help='list MIDI controllers')

  args = parser.parse_args()
  if args.midilist:
      MidiController(in_name='',mode='list')
      return
  if args.miditest is not None:
     MidiController(in_name=args.miditest,mode='test')
     return
  config =dict()
  for configfile in args.config:
     newconfig = get_yaml(configfile)
     if newconfig is None:
        return
     else:
        config.update(newconfig)
  



  loops_brother = asyncio.get_event_loop()
  scheduler = AsyncIOScheduler()
  logging.debug("Running main loop")
  # This is where update tasks go.
  callback, stream = make_stream()
  asyncio.create_task(event_processor(stream))
  modules['midi'] = MidiIntegration(config['controller'],callback=callback)
  modules['linker'] = Linker(config,callback)
  if config.get('pipewire') is not None:
    devicemap = config['pipewire'].get('devices',dict())
    modules['pipewire'] = PipewireService(devicemap,callback=callback)
    asyncio.create_task(modules['pipewire'].realtime_start())

  await asyncio.wait(asyncio.all_tasks())
  
asyncio.run(main())
