import mido
from lcd_7bit_font import lcd_7bit_render
from unidecode import unidecode
from typing import List
from enum import Enum
import logging

class Control(Enum):
    FADER = 70
    LED_RING = 80
    LED_METER = 90


class Note(Enum):
    LED_KNOB = 0
    PREVIOUS = 20
    NEXT = 21
    STOP = 22
    PLAY = 23
    BANK_LEFT = 25
    BANK_RIGHT = 26
    CH_LEFT = 27
    CH_RIGHT = 28
    LED_METER = 90    
    FADER = 110
    MUTE = 29
    VU_ENABLE = 24
    ADD_MARKER = 13


class Color(Enum):
    BLACK = 0
    RED = 1
    MAGENTA = 5
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    WHITE = 7
    CYAN = 6
    def __init__(self, value):
        if len(self.__class__):
            # make links
            all = list(self.__class__)
            first, previous = all[0], all[-1]
            previous.next = self
            self.previous = previous
            self.next = first

class Invert(Enum):
    NONE = 0
    TOP = 1
    BOTTOM = 2
    BOTH = 3

#TODO Make them accept either Enum tuples or ints.
class MidiController:
    def __init__(self, in_name: str,out_name: str = None,callback = None) -> None:
        # This is because I found that because of the way windows works,
        # you can end up with a 'device 1' input and a 'device 2' output that is really the same device.
        print(in_name)
        self._name = self.find_midi_input(in_name)
        self.midimap = dict()
        self._external_callback = None
        if out_name is None:
            out_name = in_name
        # Note - this is the callback for the filtered event, not the rawmidi event
        if callback is not None:
            logging.debug("Adding callbacks" + str(callback))
            self._external_callback = callback
            self._port_in = mido.open_input(self._name, callback = self._midi_message_in )
            self._port_out = mido.open_output(self.find_midi_output(out_name))
        else:
            logging.debug("No callback provided - starting without them")
            self._port_in = mido.open_input(self._name, callback = self._midi_message_in)
            self._port_out = mido.open_output(self.find_midi_output(out_name))

    def _midi_message_in(self,m: mido.Message):
      typemap = {
        'control_change': ['control','control'],
        'note_on': [ 'note', 'note' ],
        'note_off': ['note', 'note' ],
        'polytouch': ['polytouch', 'note' ],
        'pitchwheel':[ 'pitchwheel', 'pitch' ],
      }
      typedetail = typemap.get(m.type,None)
      output = None
      #print(self.midimap)
      if typedetail is not None:
        msgtype = self.midimap.get(typedetail[0], dict())
        callbacks = msgtype.get(getattr(m,typedetail[1]),None)
        #print(typedetail,msgtype,callbacks)
        if (callbacks is not None):
          for cb in callbacks:
             output = cb(m)
             output.update({ 'eventtype': 'change', 'source': 'midicontroller'})
             self._external_callback(output)
      if output is None:
        output = { 'message' : m }
        output.update({ 'eventtype': 'unknown-message', 'source': 'midicontroller'})
        self._external_callback(output)

    def register(self,callback,msgtype,messagevalue):
      if self.midimap.get(msgtype,None) is None:
        self.midimap[msgtype] = dict()
      cblist = self.midimap[msgtype].get(messagevalue, None)
      if cblist is None:
        self.midimap[msgtype][messagevalue] = list()
      self.midimap[msgtype][messagevalue].append(callback) 

    def find_midi_input(self, name) -> str:
        logging.debug("MIDI inputs: %s" % mido.get_input_names())
        for input_name in mido.get_input_names():
            if input_name.startswith(name):
                logging.debug("Using  MIDI device %s" % input_name)
                return input_name

        raise Exception('No input found with name %s' % name)
    
    def find_midi_output(self, name) -> str:
        logging.debug("MIDI outputs: %s" % mido.get_output_names())
        for output_name in mido.get_output_names():
            if output_name.startswith(name):
                logging.debug("Using  MIDI device %s" % output_name)
                return output_name

        raise Exception('No output found with name %s' % name)
    

    def reset(self) -> None:
        #for n in range(1, 35):
        #    self._send(mido.Message('note_on', note=n, velocity=0))

        #self.control_change(Control.FADER, 0)
        #self.segment_display_update('')
        #self.lcd_display_update('')
        return

    def note_on(self, note, velocity: int) -> None:
        if isinstance(note,Note):
          note = note.value
        self._send(mido.Message('note_on', note=note, velocity=velocity))

    def note_off(self, note: int, velocity: int) -> None:
        if isinstance(note,Note):
          note = note.value
	   
        self._send(mido.Message('note_on', note=note, velocity=velocity))

    def note_off(self, note: int, velocity: int) -> None:
        self._send(mido.Message('note_off', note=note, velocity=velocity))

    def control_change(self, control:int, value: int) -> None:
        self._send(mido.Message('control_change', control=control, value=value))

    def polytouch(self, note: int, value: int) -> None:
        self._send(mido.Message('polytouch', note=note, value=value))    
    
    def pitchwheel(self, channel: int, pitch: int) -> None:
        self._send(mido.Message('pitchwheel', channel=channel, pitch=pitch)) 

    def aftertouch(self, channel: int, value: int) -> None:
        self._send(mido.Message('aftertouch', channel=channel, value=value))
    
    def sysex(self, data: List[int]) -> None:
        self._send(mido.Message('sysex', data=data))

    def control_change(self, control:int, value: int) -> None:
        self._send(mido.Message('control_change', control=control, value=value))

    def polytouch(self, note: int, value: int) -> None:
        self._send(mido.Message('polytouch', note=note, value=value))    
    
    def pitchwheel(self, channel: int, pitch: int) -> None:
        self._send(mido.Message('pitchwheel', channel=channel, pitch=pitch)) 

    def aftertouch(self, channel: int, value: int) -> None:
        self._send(mido.Message('aftertouch', channel=channel, value=value))
    
    def sysex(self, data: List[int]) -> None:
        self._send(mido.Message('sysex', data=data))

    def _send(self, message: mido.Message) -> None:
        self._port_out.send(message)
    
    def lcd_display_update(self, characters: str, color: Color = Color.WHITE, invert: Invert = Invert.NONE):
        self.sysex(self._create_lcd_display_data(characters,color,invert))

    def _create_lcd_display_data(self, characters: str, color: Color, invert: Invert) -> List[int]:
        characters = unidecode(characters)
        character_data = self._pad_to(list(map(ord, characters[:14])), 14)
        color_code = color.value | (invert.value << 4)

        return [0x00, 0x20, 0x32, 0x41, 0x4c, 0x00, color_code] + character_data

    def segment_display_update(self,characters: str):
        self.sysex(self._create_segment_display_data(characters))
        
    def _create_segment_display_data(self, characters: str) -> List[int]:
        characters = unidecode(characters)
        character_data = self._pad_to(lcd_7bit_render(characters[:12]), 12)

        return [0x00, 0x20, 0x32, 0x41, 0x37] + character_data + [0x00, 0x00]

    @staticmethod
    def _pad_to(data: List[int], n: int) -> List[int]:
        trimmed = data[:n]
        return trimmed + [0] * (n - len(trimmed))

