import logging
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
    
    for controller in config['link'].keys():
      if controller == 'virtual':
        continue
      for control,destination in config['link'][controller].items():
        self.add_links(controller,control,destination)
    # We map the normal controls first so we can get the links when we backlink the virtuals.
    for virtcontrol,virtsetup in config['link']['virtual'].items():
          for target in virtsetup['targets']:
            realdetail = self._links['virtual'][virtcontrol]
            realaction = list(realdetail.keys())[0] # volume
            realcontroldetail = realdetail[realaction] # { 'xtouch' : prev_chan }
            realcontroller = list(realcontroldetail.keys())[0] # 'xtouch' 
            realcontrol = realcontroldetail[realcontroller] # 'prev_chan' 
            
                        #pipewire              'HDMI 5.1'
            self._links[virtsetup['system']][target['target']][realaction][realcontroller] = realcontrol

  #def self.add_virtual_backlink():
  
  def add_links(self,controller,control,endpoint):
     
     interface = list(endpoint.keys())[0] # eg pipewire
     actiondetail = list(endpoint.values())[0] # eg volume: 'HDMI 5.1'

       
     action = list(actiondetail.keys())[0] # volume
     itemname = list(actiondetail.values())[0] # 'HDMI 5.1'
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
    logging.debug('Virtal {} set to {}'.format(virttarget,target['target']))
    virtdetails['_current'] = index
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
    print("numtargets:",numtargets)
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
         logging.fatal("No ID in message:",message)
       action = self._links[message['id']][message['item']]
       print("action",action)
       if not message.get('pressed',True):
         return
       if action != {} and list(action.keys())[0] == "virtual":
          print("virtual mapping")
          action = self.get_real_action(list(action.values())[0])
       # once translated to a real action, we keep going normally.
       if action != {}:
         action.update(self.translate_to_target(message))
         self.send_message(action,list(action.keys())[0])
     else:
       
       actions = self._links.get(message['source'],dict()).get(message['item'],None)
       if actions is None:
         return
       
       for action in actions.values(): # eg, volume,mute. all we really need are the values
         # action is { 'controller' : 'control' }
         control = list(action.values())[0]
         controller = list(action.keys())[0]
         if controller == 'virtual':
           target = self.get_virt_target(control) # Target is { 'backend', 'device'}
           # Who knows wtf is going on here.
           device = list(action.values())[0]
           backend = list(action.keys())[0]
           # we cache it regardless, because we can cycle back
           self._virtuals[control]['cachedmessage'] = message 
           if (device == message['item']): # The current selection is 
             # now we need to get the actual control name to send it to
             controller = 'TODO'
           else:  
             self._virtuals[control]['cachedmessage'] = message
           return
         outmessage = self.translate_to_midi(message,(controller,control))
         self.send_message(outmessage,'midi')
       
  def translate_to_midi(self,message,midicontrols):
    output = dict()
    print('midicontrols',midicontrols)
    control = self._config['controller']['controls'][midicontrols[1]]
    output['id'] = midicontrols[0]
    output['item'] = midicontrols[1]
    print(control)
    print('translating',message)
    match control['type']:
      case 'button':
        #if message.get('value',None) is not None: output['value'] = bool(message['value']) 
        output['value'] = message['data']['mute']
      case 'fader':
        output['value'] = int(min(message['data']['volume']*96,127)) # 96 = 0db
    return output

  def translate_to_target(self,message):
    output = dict()
    control = self._config['controller']['controls'][message['item']]
    match control['type']:
      case 'button':
        if message.get('value',None) is not None: output['value'] = bool(message['value']) 
        if message.get('pressed',None) is not None: output['pressed'] = bool(message['pressed']) 
      case 'fader':
        if message.get('value',None) is not None: output['value'] = float(message['value'])/96.0 # 96 = 0db
    return output





  def send_message(self,messagedata,destination):
    message = { 'source': 'linker',
                'destination': destination
              }
    message.update(messagedata)
    self._callback(message)
    