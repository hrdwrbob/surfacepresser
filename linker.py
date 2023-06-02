

class Linker:
  _config=dict()
  _links =Vividict()
  _virtuals =Vividict()
  def __init__(self, config,callback) -> None:
    self._config = config
    self._virtuals = config.get('virtual',None)
    self._callback = callback
    for controller in config['link'].keys():
      for control,destination in config['link'][controller].items():
        self.reverselink(controller,control,destination)
  
  def add_links(self,controller,control,endpoint):
     
     interface = list(endpoint.keys())[0] # eg pipewire
     action = list(endpoint.values())[0] # eg volume: 'HDMI 5.1'

       
     itemtype = list(action.keys())[0] # volume
     itemspecific = list(action.values())[0] # 'HDMI 5.1'
     # Forward link (from the midi control surface to the library or internal function:
     self._links['controller']['control'] = action
     # reverse link (i.e. from the library to midi)
     self._links[interface][itemspecific][itemtype][controller] = control

  def virtual_action:
    if self._virtuals is None: return
    
  
  def get_real_virtual_action(virtualname):
    if self._virtuals is None: return
    
     

  async def receive_message(self,message):
     if message['source'] == 'midicontroller':
       # example message values                xtouch                 fader
       # Action will be eg { 'pipewire' : { 'volume' : 'HDMI 5.1' }
       action = self._links[message['id']][message['item']]
       if not message.get('pressed',True):
         return
       if action is not None and list(action.keys())[0] == "virtual"
         virt_action(
       if action is not None
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


  def send_message(self,messagedata,destination):
    message = { 'source': 'linker',
                'destination': destination
              }
    message.update(messagedata)
    self._callback(message)
       
class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)() # retain local pointer to value
        return value                     # faster to return than dict lookup
