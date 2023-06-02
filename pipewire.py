#!/usr/bin/env python3
import logging
import dumper
import json
import subprocess
import asyncio
from deepdiff import DeepDiff 

#pwdump = subprocess.run(['pw-cli','set-param',str(nodeid),'Props',json.dumps(props)],capture_output=True,text=True)

def noop(*args, **kwds):
    return args[0] if args else None

# A relatively simple integration with pipewire that allows you to set volume and connections.

class PipewireService:
  pwdata = dict()
  pwsinks = dict()
  pwsources = dict()
  pwdevices = dict()
  pwnodes = dict()
  pwnodesbyname = dict()
  pwlinks = dict()
  pwports = dict()
  aliasmap = dict()
  callback = noop()
  async def receive_message(self,message):
    print("pipewire received",message)
    action = list(message['pipewire'].keys())[0]
    nodename = list(message['pipewire'].values())[0]
    value = message.get('value',None)
    print('pipewire',action,nodename,value)
    if value is None: return
    
    if action in ('volume'):
       self.pwnodesbyname[nodename].setvolume(value)
    if action in ('mute'):
       self.pwnodesbyname[nodename].setmute(value)
    

  async def realtime_start(self):
    logging.warning("Starting pipewire realtime data loop")
    output=""
    pwdump = await asyncio.create_subprocess_shell('pw-dump -m -N',stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    logging.warning("Created pipewire Subprocess")
    while True:
       thisoutput = await pwdump.stdout.readline()
       #logging.warning("Pipewire Got data portion: " + thisoutput.decode('utf-8'))
       output += thisoutput.decode('utf-8')
       if ']\n' == thisoutput.decode('utf-8'):
         logging.info("Pipewire Got data")
         self.callback(self._parse_json(output))
         output=""

  def get_pw(self):
     pwdump = subprocess.run(['pw-dump','-N'],capture_output=True,text=True)
     self._parse_json(pwdump.stdout)

  def __init__(self,aliasmap,callback=None):
    self.aliasmap = aliasmap
    if callback is not None:
      self.callback = callback
    
  def _device_add(self,node):
    self.pwdevices[node.name] = node

  def _source_add(self,node):
    self.pwsources[node.name] = node

  def _sink_add(self,node):
    self.pwsinks[node.name] = node

  def _parse_json(self,encoded_json):    
    pipewire = json.loads(encoded_json.replace("' ",'" ').replace(" '",' "')) # This is a travesty of immense proportions
    name = "unknown"
    changes = None
    returnval = list()
    for node in pipewire:
      # skip nodes we don't care about - suspended nodes and root node, nodes without info.
      if (
         node.get('info',None) is None or
         node.get('info',dict()).get('state',None)  == "suspended" or
         node['id'] == 0 
         ):
        continue

      event = {'source': "pipewire" }
      event['item'] = node.get('name','unknown')
        
      # Special case for deleted nodes.
      if node['info'] is None:
        event['changetype'] = 'delete'
        event['nodeid'] = node['id']
        self._delete_node(node['id'])
        returnval.append(event)
        continue
        
      nodetypemap = { 'PipeWire:Interface:Link': self.pwlinks,
                      'PipeWire:Interface:Node': self.pwnodes,
                      'PipeWire:Interface:Port': self.pwports,
                    }


      nodelist = nodetypemap.get(node['type'],None)
      if nodelist is None:
        continue

      if node['id'] not in (nodelist.keys()):
        # This is a new node.
        self._node_add(node) # new node
        event['changetype'] = 'new'
        event['data'] = nodelist[node['id']].simple_dict()

      else:
        # Changed node, build a change object
        oldnode = nodelist[node['id']].simple_dict()
        self._node_add(node)
        newnode = nodelist[node['id']].simple_dict()
        event['changetype'] = 'change'
        event['nodeid'] = node['id']
        changes = DeepDiff(oldnode,newnode)
        event['data'] = nodelist[node['id']].simple_dict()
        event['item'] = event['data'].get('name','unknown')
        event['changes'] = changes

      returnval.append(event)
          

    return returnval

  def _node_delete(self,id):
    # IDs are unique so we can take a nice shortcut here. 
    for pwlist in (self.pwsinks, self.pwsources, self.pwdevices, self.pwnodes, self.pwlinks, self.pwports):
      if id in pwlist.keys():
        del pwlist[id]


  def _node_add(self,node):
    mynode = PipewireNode(node)
    mapped_name =  self.aliasmap.get(mynode.name,None) 
    if mapped_name is not None:
      mynode.name = mapped_name
    self.pwnodesbyname[mynode.name] = mynode
    if (node['type'] == "PipeWire:Interface:Device"):
      self.pwnodes[node['id']] = mynode
      if node['info']['props']['media.class'] == "Audio/Device":
        self._device_add(mynode)
        #print(node['info'])
        #print(node['info']['props']['device.nick'])
    elif (node['type'] == "PipeWire:Interface:Node"):
      self.pwnodes[node['id']] = mynode
      #print(node['info']['props'].get('node.nick'),"None")
      #print(node['info']['props'].get('node.name'),"None")
      #print(node['info']['props'].get('node.description',"None"))
      devclass = node['info']['props'].get('media.class',"None")
      if devclass == "Audio/Sink":
        self._sink_add(mynode)
      elif devclass == "Audio/Source":
        self._source_add(mynode)
      elif devclass == "Midi/Bridge":
        pass
      elif devclass == "Video/Source":
        pass
      elif devclass == "Video/Sink":
        pass
      elif devclass == "Stream/Input/Audio": # sink is "input" because consistency
        self._sink_add(mynode)
      elif devclass == "Stream/Output/Audio":
        self._source_add(mynode)
      else:
          pass
    elif (node['type'] == "PipeWire:Interface:Port"):
      # print(node['info'])
      self.pwports[node['id']] = mynode
      pass
    elif (node['type'] == "PipeWire:Interface:Link"):
      self.pwlinks[node['id']] = mynode
      self.pwnodes[node['info']['output-node-id']].addoutlink(node['info']['input-node-id'])
      self.pwnodes[node['info']['input-node-id']].addinlink(node['info']['output-node-id'])
  
 

class PipewireNode:  
  name = "New"
  data =dict()
  outlinks=list()
  inlinks=list()
  pwid = None
  def __init__(self,nodedata):
    self.data = nodedata
    self.pwid = nodedata['id']
    #print(self.data)
    self.inlinks = list()
    self.outlinks = list()
    self.volume = 0   
    self.mute = None
    self.type = self.data['type'][19:]
    self.name = get_nested_dict(self.data,('info','props','node.name'))
    #if self.name is not None and "." in self.name:
    #self.name = None
  
    if self.name is None:
      self.name = get_nested_dict(self.data,('info','props','node.nick'))
    if self.name is None:
      self.name = get_nested_dict(self.data,('info','props','node.name'))
    if self.name is None:
      self.name = get_nested_dict(self.data,('info','props','application.name'))
    if self.name is None:
      self.name = get_nested_dict(self.data,('info','props','device.product.name'))
    if self.name is None:
      self.name = 'NoName'
    
    props = get_nested_dict(self.data,('info','params','Props'))
    if props is not None:
      props = props[0]
      self.volume = props.get('softVolumes',0)[0]
      self.mute = props.get('softMute',True)

  def setvolume(self,vol):
    props = get_nested_dict(self.data,('info','params','Props'))[0]
    props['softVolumes'] = [vol]*len(props['channelVolumes'])
    props['channelVolumes'] = [vol]*len(props['channelVolumes'])
    pwdump = subprocess.run(['pw-cli','set-param',str(self.pwid),'Props',json.dumps(props)],capture_output=True,text=True)
    
  def setmute(self,mute):
    props = get_nested_dict(self.data,('info','params','Props'))[0]
    print(props)
    print(props['softMute'],mute)
    if props['softMute'] != mute:
      props['softMute'] = mute
      print(props)
      print(subprocess.run(['pw-cli','set-param',str(self.pwid),'Props',json.dumps(props)],capture_output=True,text=True))
	
  def simple_dict(self):
    simpledict = dict()
    simpledict['id'] = self.pwid
    simpledict['type'] = self.data['type'][19:]
    if self.type == "Link":
      simpledict['fromnode'] = get_nested_dict(self.data,('info','props','link.input.node'))
      simpledict['fromport'] = get_nested_dict(self.data,('info','props','link.input.port'))
      simpledict['tonode'] = get_nested_dict(self.data,('info','props','link.output.node'))
      simpledict['toport'] = get_nested_dict(self.data,('info','props','link.output.port'))
      simpledict['to'] = 1
    if self.type == "Node":
      simpledict['name'] = self.name
      simpledict['inlinks'] = self.inlinks 
      simpledict['volume'] = self.volume
      simpledict['mute'] = self.mute
      simpledict['outlinks'] = self.outlinks
    return simpledict

  def addoutlink(self,link):
    if link not in self.outlinks:
      self.outlinks.append(link)
  
  def addinlink(self,link):
    if link not in self.inlinks:
      self.inlinks.append(link)
      


class PipewireSink(PipewireNode):
  pass
class PipewireSource(PipewireNode):
  pass

def get_nested_dict(to_search,keys):
  for key in keys:
    if to_search is None:
      break
    to_search = to_search.get(key,None)
  if isinstance(to_search,dict) and  to_search.keys() == 0:
    return None
  return to_search




