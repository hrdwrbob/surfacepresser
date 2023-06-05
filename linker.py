import logging
from scitools.StringFunction import StringFunction
from scipy.interpolate import interp1d

class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)() # retain local pointer to value
        return value                     # faster to return than dict lookup


class Linker:
  _config=dict()
  _links =Vividict()
  _virtuals =Vividict()
  def __init__(self, config,callback) -> None:
    self._config = config
    self._virtuals.update(config['link'].get('virtual',dict()))
    self._callback = callback
    # set virtual device default
    for virtname,virtualbackend in self._virtuals.items():
      self.update_virt_target(virtname,0)
      for targetdetails in virtualbackend['targets']:
        virtualbackend[targetdetails['target']] = dict()
    for controller in config['link'].keys():
      if controller == 'virtual':
        continue
      for control,destination in config['link'][controller].items():
        self.add_links(controller,control,destination)
    # We map the normal controls first so we can get the links when we backlink the virtuals.
    for virtcontrol,virtsetup in config['link']['virtual'].items():
          for target in virtsetup['targets']:
            realdetail = self._links['virtual'][virtcontrol] 
            realaction,realcontroldetail = list(realdetail.items())[0] # volume, { 'xtouch' : prev_chan }
            realcontroldetail = realdetail[realaction] # 
            realcontroller, realcontrol = list(realcontroldetail.items())[0] # 'xtouch', 'prev_chan
                        #pipewire              'HDMI 5.1'
            self._links[virtsetup['system']][target['target']][realaction]['virtual'] = virtcontrol

  #def self.add_virtual_backlink():
  
  def add_links(self,controller,control,endpoint):
     
     (interface,actiondetail) = list(endpoint.items())[0] # eg pipewire, { volume: 'HDMI 5.1'}
     (action,itemname) = list(actiondetail.items())[0] # volume, 'HDMI 5.1'
     # Forward link (from the midi control surface to the endpoint
     self._links[controller][control] = endpoint
     # reverse link (i.e. from the library to midi)
     self._links[interface][itemname][action][controller] = control

  def virtual_action(self,):
    if self._virtuals is None: return
    
  def update_virtual_links(self,virtdetails,index):
    target = virtdetails['targets'][index] 
    display = virtdetails.get('display',None)
    if display is not None:
      text = target.get('text',None)
      if text is None: # Default to target
        text = target['target']
      color = target.get('color',virtdetails.get('color','white'))
      invert = target.get('invert',virtdetails.get('invert',False))
      displaymessage = { 'id': list(display.keys())[0],
                        'item': list(display.values())[0],
                        'color': color,
                        'invert': invert,
                        'value': text
                        }
      self.send_message(displaymessage,'midi')
      
  def update_virt_target(self,virttarget,index):
    virtdetails = self._virtuals[virttarget]
    target = virtdetails['targets'][index] 
    textname = target.get('text',"")
    if textname != "":
      textname = ' ({})'.format(textname)
    logging.debug('Virtual {} set to {}'.format(virttarget,target['target']) + textname)
    virtdetails['_current'] = index
    # Now update all relevant controls
    message = self._virtuals[virttarget].get(target['target'],dict()).get('cachedmessage',None)
    if message is not None:
      for controldetail in self._links['virtual'][virttarget].values():
        (controller,control) = list(controldetail.items())[0]
        # Get action for the control.
        action = list(self._links[controller][control]['virtual'].keys())[0]
        outmessage = self.translate_to_midi(message,(controller,control),action)
        self.send_message(outmessage,'midi')
    self.update_virtual_links(virtdetails,index)
    
  def get_virt_target(self,virttarget):
    virtdetails = self._virtuals[virttarget]
    target = virtdetails['targets'][virtdetails['_current']] 
    return target

  def get_real_action(self,virtualaction):
    (action,virttarget) = list(virtualaction.items())[0]
    noreal = False
    virtdetails = self._virtuals[virttarget]
    # What is our current value / are we changing
    numtargets = len(virtdetails['targets'])
    index = virtdetails.get('_current',-1)
    if index == -1:
      self.update_virt_target(virttarget,index)
    value = 0
    if action == "next":
      value = +1
    if action == "prev":
      value = -1
    if value != 0:
      noreal= True
      index = (index+value) % numtargets
      self.update_virt_target(virttarget,index)


    if (noreal):
      return {}
    target = virtdetails['targets'][virtdetails['_current']] 
    system = target.get('system',virtdetails.get('system',None))
    realaction = { system : { action : target['target'] } }
    print("real action",realaction)
    return realaction
    


  async def receive_message(self,message):
     if message['source'] == 'midicontroller':
       # example message values                xtouch                 fader
       # Action will be eg { 'pipewire' : { 'volume' : 'HDMI 5.1' }
       id = message.get('id',None)
       if id is None:
         logging.error("No ID in message:",message)
         return
       action = self._links[message['id']][message['item']]
       if not message.get('pressed',True):
         return
       if action != {} and list(action.keys())[0] == "virtual":
          action = self.get_real_action(list(action.values())[0])
       # once translated to a real action, we keep going normally.
       if action != {}:
         action.update(self.translate_to_target(message,action))
         self.send_message(action,list(action.keys())[0])
     else:
       actions = self._links.get(message['source'],dict()).get(message['item'],None)
       if actions is None:
         return
       
       for action, actiondetail in actions.items(): # ignore action and send to all
         controller, control = list(actiondetail.items())[0] # { xtouch : prev_chan }
         if controller == 'virtual': 
           # Get the current target to see if we need to update now
           logging.debug("received message for item {} to virtual target {}".format(message['item'],control))
           target = self.get_virt_target(control) # Target is { 'backend', 'device'}
           backend, device = list(target.items())[0]
           # we cache it regardless, because we can cycle back
           self._virtuals[control][message['item']]['cachedmessage'] = message 
           if (device == message['item']): # The message is for the current selection
             # now we need to get the actual control names to send it to midi
             for realcontroller, realcontrol in self._links['virtual'][control][action].items():
               outmessage = self.translate_to_midi(message,(realcontroller,realcontrol),action=action)
               self.send_message(outmessage,'midi')
         else:
           outmessage = self.translate_to_midi(message,(controller,control),action=action)
           self.send_message(outmessage,'midi')
       

  
  def get_midi_translation(self,source,value,midicontrols,action):
    datamap = self._config[source]['datamap'].get(action,None)
    if datamap is None:
      return value
    function = datamap.get('from_function',None)
    if function is not None:
      f = StringFunction(function)
      return f(value)
    elif datamap.get('map',None) is not None:
      midimap = datamap['map']['midi']
      itemmap = datamap['map'][source]
      get_output = interp1d(itemmap, midimap)
      midivalue =  int(get_output(value))
      print("Message:",source,midicontrols,action)
      print("input",value,"midivalue:",midivalue)
      return midivalue
    else:
      return value
    
  def translate_to_midi(self,message,midicontrols,action):
    output = dict()
    control = self._config['controller']['controls'][midicontrols[1]]
    output['id'] = midicontrols[0]
    output['item'] = midicontrols[1]
    if message['data'].get(action, None) is not None:
      output['value'] = self.get_midi_translation(message['source'],message['data'][action],midicontrols,action)
    return output
  
  def get_target_translation(self,message,midicontrols,action):
    # Action will be eg { 'pipewire' : { 'volume' : 'HDMI 5.1' }
    backend, action = list(action.items())[0]
    action, target = list(action.items())[0]
    datamap = self._config[backend]['datamap'].get(action,None)
    if datamap is None:
      return message['value']
    function = datamap.get('to_function',None)
    if function is not None:
      f = StringFunction(function)
      return f(message['value'])
    elif datamap.get('map',None) is not None:
      midimap = datamap['map']['midi']
      itemmap = datamap['map'][backend]
      get_output = interp1d(midimap, itemmap)
      return float(get_output(message['value']))
    else:
      return message['value']
    
  def translate_to_target(self,message,action):
    output = dict()
    control = self._config['controller']['controls'][message['item']]
    # Translate the value
    if message.get('value',None) is not None:
      output['value'] = self.get_target_translation(message,control,action)
    # Add other details if present.
    if message.get('pressed') is not None:
      output['pressed'] = bool(message['pressed']) 
    return output





  def send_message(self,messagedata,destination):
    message = { 'source': 'linker',
                'destination': destination
              }
    message.update(messagedata)
    self._callback(message)
