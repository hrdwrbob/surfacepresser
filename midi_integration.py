from midi_controller import  MidiController, Note, Control, Color, Invert
import logging
import time
import asyncio
import math
from itertools import chain
from deepdiff import DeepDiff
from scipy.interpolate import interp1d
from apscheduler.schedulers.asyncio import AsyncIOScheduler




class Display():
  pass

class SegmentDisplay(Display):
  pass


class LcdDisplay(Display):
  pass
  
class Control():
  _midicontrol = None
  _state = dict()
  # placeholder

  def recv_message(self):
    pass

  def msg_callback(self,message):
    old_state = dict(self._state)
    self.recv_message(message)
    message = { 'item' : self._config['name'],
                'id'   :  self._config['deviceid'] }
    for i in self._state.keys():
      if old_state[i] != self._state[i]:
      	message[i] = self._state[i]
    return message

  def __init__(self, midicontrol = None,config = None) -> None:
    self._config = config
    self._state.update(config) # include config in state
    self._midicontrol = midicontrol
    for msgtype in ('note','control'):
      if msgtype in self._config.keys():
        self._midicontrol.register(self.msg_callback,msgtype,self._config[msgtype])

  def get_state():
    state = self._state
    return state

class LevelControl(Control):
  _state = dict()
  _state['lockout'] = False
  _state['touched'] = False
  _state['value'] = 0
  def __init__(self, midicontrol = None,config = None) -> None:
    super().__init__(midicontrol = midicontrol,config=config)

  def set_value(self,value):
    if self._state['lockout'] is False:
      self._state['value'] = value
      self._midicontrol.control_change(self._config['control'],value)
  
  def recv_message(self,m):
    if m.type == 'control_change':
        self._state['value'] = value

class FaderControl(LevelControl):
  def __init__(self, midicontrol = None,config = None) -> None:
    super().__init__(midicontrol = midicontrol,config=config)

  def recv_message(self,m):
    if m.type == 'control_change':
        self._state['value'] = m.value
    if m.type == 'note_on':
      if m.velocity == 127:
        self._state['lockout'] = True
      else:
        self._state['lockout'] = False
        





class ButtonControl(Control):
  _state = dict()
  # Start with true so it resets the light.
  _state['light'] = True 
  _state['lockout'] = False
  _state['pressed'] = False
  _state['value'] = False
  def __init__(self, midicontrol = None,config = None) -> None:
    self._light_style =  config.get('light','state')
    self._button_style = config.get('style','toggle')
    super().__init__(midicontrol = midicontrol,config=config)
    self.light_update()


  def light_update(self):
    match(self._light_style):
      case "always_on":
        self._light_switch(True)
      case "momentary":
        self._light_switch(self._state['pressed'])
      case "state":
        self._light_switch(self._state['value'])


  def _light_switch(self,state):
    if state is self._state['light']:
      return
    else:
      self._state['light'] = state
      if state:
        self._midicontrol.note_on(self._config['note'], 127)
      else:
        self._midicontrol.note_on(self._config['note'], 0)

  def set_value(self,value):
    self._state['value'] = value
    self.light_update()
  
  def recv_message(self,m):
    if m.velocity == 127: # down
      self._state['pressed'] = True
      if (self._button_style == 'toggle'):
        self._state['value'] = not self._state['value']
      elif (self._button_style == 'momentary'):
        self._state['value'] = True

    if m.velocity == 0: # down
      self._state['pressed'] = False
      if (self._button_style == 'momentary'):
        self._state['value'] = False
    self.light_update()
    
      
       
    
class RotaryControl(Control):
  pass


class JogWheelControl(LevelControl):
 pass

class SliderControl(LevelControl):
  async def touch(self,midi):
    # I'm assuming touch is the same for all sliders, this is probably not the case, because MIDI is a disaster.
    if midi.velocity == 0:
      self.lockout = True
    elif midi.velocity == 127:
      await asyncio.sleep(self._config['touch']['timeout']/1000)
      self.lockout = False
      self.update_slider()
      
class KnobControl(LevelControl):
  pass

   
class MidiIntegration:
    classmap = {
               'fader' : FaderControl,
               'rotary' : RotaryControl,
               'level'  : LevelControl,
               'button'  : ButtonControl,
               'jog_wheel' : JogWheelControl,
               'segment' : SegmentDisplay,
               'lcdtext' : LcdDisplay,
              }
  
    def __init__(self, config: dict,callback = None) -> None:
        self._controller = MidiController(config['midiname'],callback=callback)
        self._controller.reset()
        #self.lcd_color = Color.CYAN
        #self._controller.segment_display_update("")
        #self._segment_lock = False
        #self._display_lock_seconds = 0
        self._controls = dict()
        self._midimap = dict()
        controls = config.get('controls',dict())
        for control in controls.keys():
          controlconfig = controls[control]
          controlconfig['name'] = control
          controlconfig['deviceid'] = config['id']
          self._add_control(control,controlconfig)

    def _add_control(self,name,controlconfig):
      newcontrol = self.classmap[controlconfig['type']](self._controller,controlconfig)
      self._controls[name] = newcontrol

    # If we're not using callback.
    def get_midi_input(self):
        for msg in self._controller.get_input():
            self._handle_midi_input(msg)
    async def receive_message(self,message):
      print("midi received",message)
      if 'value' in message.keys():
        self._controls[message['item']].set_value(message['value'])
      return
