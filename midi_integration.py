from midi_controller import  MidiController, Note, Color, Invert
import logging
import time
import asyncio
import math
from itertools import chain
from deepdiff import DeepDiff
from scipy.interpolate import interp1d
from apscheduler.schedulers.asyncio import AsyncIOScheduler





  
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

  def get_state(self):
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
        self._state['value'] = m.value

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
  
  _state['light'] = False
  _state['lockout'] = False
  _state['pressed'] = False
  _state['value'] = False
  def __init__(self, midicontrol = None,config = None) -> None:
    self._light_style =  config.get('light','state')
    self._button_style = config.get('style','toggle')
    super().__init__(midicontrol = midicontrol,config=config)
    self.light_update(force=True)
    
    


  def light_update(self,force=False):
    match(self._light_style):
      case False:
        self._light_switch(False,force)
      case "always_on":
        self._light_switch(True,force)
      case "momentary":
        self._light_switch(self._state['pressed'],force)
      case "state":
        self._light_switch(self._state['value'],force)


  def _light_switch(self,state,force=False):
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
    
      
       
    
class RotaryControl(LevelControl):
  pass




class JogWheelControl(Control):
  def __init__(self, midicontrol = None,config = None) -> None:
    super().__init__(midicontrol = midicontrol,config=config)
  def recv_message(self,m):
    if m.value == 65: 
      self._state['direction'] = "1"
    if m.value == 0: 
      self._state['direction'] = "-1"

  def msg_callback(self,message):
    self.recv_message(message)
    message = { 'item' : self._config['name'],
                'id'   :  self._config['deviceid'] }
    message['direction'] = self._state['direction']
    return message

class SliderControl(LevelControl):
  async def touch(self,midi):
    # I'm assuming touch is the same for all faders, this is probably not the case, because MIDI is a disaster.
    if midi.velocity == 0:
      self.lockout = True
    elif midi.velocity == 127:
      await asyncio.sleep(self._config['touch']['timeout']/1000)
      self.lockout = False
      self.update_slider()
      
class KnobControl(LevelControl):
  pass




class Display(Control):
  pass

class BgrSegmentDisplay(Display):
  pass



class XTOScribbleStrip (Display):
  _display_settings = dict()
  def set_text(self,text):
    self._display_settings['characters'] = text
    self.update_display()
  
  def __init__(self, midicontrol = None,config = None) -> None:
    self._display_settings['color'] = Color.WHITE
    self._display_settings['invert'] = Invert.NONE
    self._display_settings['characters'] = "              "
    super().__init__(midicontrol = midicontrol,config=config)    
  
  def update_display(self,message=None):
     if message is not None:
       self.set_color(message['color'])
       self.set_invert(message['invert'])
       self.set_text(message['value'])
     self._midicontrol.lcd_display_update(**self._display_settings)
  
  def set_invert(self,invert: bool):
    if invert:
      self._display_settings['invert'] = Invert.BOTH
    else:
      self._display_settings['invert'] = Invert.NONE


  def set_color(self,colorname: str):
    colorname = colorname.upper()
    try:
      color = Color[colorname]
    except:
      color = Color.WHITE
    self._display_settings['color'] = color

class XTOScribbleHalf(Display):
  minion = True
  def __init__(self,display : Display,location) -> None:
    self._location = location
    self._display = display
    
  def set_color(self,colorname: str):
    self._display.set_color(colorname)

  def set_text(self,text):
    text = "{:^7}".format(text[:7])
    if self._location == "top":
      bottom = self._display._display_settings['characters'][7:14]
      self._display._display_settings['characters'] = text + bottom
    if self._location == "bottom":
      top = self._display._display_settings['characters'][:7]
      self._display._display_settings['characters'] = top + text

  def update_display(self,message=None):
    if message is not None:
       self.set_color(message['color'])
       self.set_invert(message['invert'])
       self.set_text(message['value'])
    self._display.update_display()

     
  def set_invert(self,invert: bool):
    invertstate = self._display._display_settings['invert']
    state = dict()
    state['bottom'] = invertstate == Invert.BOTH or state == Invert.BOTTOM
    state['top'] = invertstate == Invert.BOTH or state == Invert.TOP
    mystate = state[self._location]
    # I'm sure there's a better way, but here we are.
    if self._location == 'top':
      other = 'bottom'
      otheron = Invert.BOTTOM
      inverton = Invert.TOP
    else:
      other = 'top'
      otheron = Invert.TOP
      inverton = Invert.BOTTOM
    otherstate = state[other]
    if (invert == mystate):
      return
    elif otherstate and invert:
      self._display._display_setting['invert'] = Invert.BOTH
    elif otherstate and not invert:
      self._display._display_setting['invert'] = otheron
    elif not otherstate and not invert:
      self._display._display_setting['invert'] = Invert.NONE
    else:
      self._display._display_setting['invert'] = inverton


class XTOScribbleTop(XTOScribbleHalf):
  def __init__(self,display) -> None:
     super().__init__(display, location='top')   

class XTOScribbleBottom(XTOScribbleHalf):
  def __init__(self,display) -> None:
    super().__init__(display, location='bottom')   
    

      
  

   
class MidiIntegration:
    classmap = {
               'fader' : FaderControl,
               'rotary' : RotaryControl,
               'level'  : LevelControl,
               'button'  : ButtonControl,
               'jogwheel' : JogWheelControl,
               'behringer_segment' : BgrSegmentDisplay,
               'behringer_one_scribble' : XTOScribbleStrip,
               'behringer_one_scribble_top' : XTOScribbleTop,
               'behringer_one_scribble_bottom' : XTOScribbleBottom,
               
              }
  
    def __init__(self, config: dict,callback = None) -> None:
        self._controller = MidiController(config['midiname'],callback=callback)
        self._controller.reset()
        self._lock = asyncio.Lock()
        self._config = config
        self._controls = dict()
        self._displays = dict()
        displays = config.get('displays',dict())
        for display in displays.keys():
          displayconfig = displays[display]
          self._add_display(display,displayconfig)
        controls = config.get('controls',dict())
        for control in controls.keys():
          controlconfig = controls[control]
          controlconfig['name'] = control
          controlconfig['deviceid'] = config['id']
          self._add_control(control,controlconfig)

    def _add_display(self,name,displayconfig):
      displayconfig['name'] = name
      displayconfig['deviceid'] = self._config['id']
      newdisplayclass = self.classmap[displayconfig['type']]
      if getattr(newdisplayclass,'minion',False):
        realdisplay = displayconfig.get('display',None)
        if not isinstance(self._displays.get(realdisplay),Display):
          self._add_display(realdisplay,self._config['displays'][realdisplay])
        self._displays[name] = newdisplayclass(self._displays[realdisplay])
      else:
        newdisplay = newdisplayclass(self._controller,displayconfig)
        self._displays[name] = newdisplay

    def _add_control(self,name,controlconfig):
      newcontrol = self.classmap[controlconfig['type']](self._controller,controlconfig)
      print(name,controlconfig)
      self._controls[name] = newcontrol


    async def receive_message(self,message):
      async with self._lock:
        if 'value' in message.keys() and message['item'] in self._controls.keys():
          self._controls[message['item']].set_value(message['value'])
        elif 'value' in message.keys() and message['item'] in self._displays.keys():
          self._displays[message['item']].update_display(message)
        return
