
## Setup - MIDI device

Further 
Midi devices are setup with a YAML file (eg: ```xtouchone.yaml```) detailing all the available controls and displays.

```yaml
controller:
  midiname: 'X-Touch One'
  id: 'xtouch'
  controls:

   scrub:
     type: button
     note: 29
   fader:
     type: fader
     note: 110
     control: 70
    jogwheel:
      type: jogwheel
      control: 88
  displays:
    scribble_strip:
      type: behringer_one_scribble
    segment_display:
      type: behringer_segment

```
| Config item | Description |
| ----------- | ----------- |
| midiname | Name of the midi device (list them with `mido-ports`) |
| id | Unique ID of the midi controller (because it will support multiple) |
| controls | List of controls on the device. |

Control names are arbitrary strings, but I would strongly recommend simply calling them after the labels on the device. This will make it much much easier to correlate. 

Generic control config items
| Control config item | Description |
| ----------- | ----------- |
| type | Type of control. |
| note | Note value of control (for notes) |
| control | control value (for control change) |


### Types of controls
* ```rotary``` - Rotary encoder. Has LEDs to show where the value is, and a rotary encoder with a push button
 Note: The button on a rotary encoder is a seperate device and has a seperate entry.
* ```fader``` -  Fader control - Supports either motorised or non motorised faders.
The library will still send the commands for a motorised fader, They will be ignored if not supported.
* ```button`` - Button. 

* ```jogwheel``` - Jog wheel. Goes up and down. wheeeeeeeeeeeee (sends a -1 or +1)

### Types of displays
 Support is available for behringer segment (timing) displays, and LCD (channel info) because that's what I have. If you know the sysex codes for the displays, adding more is easily done.

* ```meter```
For LED level meters. 0-127 - audio level.
* ```xtouchlcd```
Supports behringer X touch One LCD. 
| Sreen config/setting item | Description |
| ----------- | ----------- |
| section | Section of the display - top, bottom, or full. There are 7 characters per section. With two seperate entries you can control them seperately.(TODO)|
| color | Screen color (black, red, green, yellow, blue, magenta, cyan, white)|
| invert | Invert LCD |
* ```xtouchsegment```
Supports behringer X touch One LCD Segment display
has up to 12 "characters" using a segment font.
