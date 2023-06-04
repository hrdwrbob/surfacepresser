# Surface Presser - A Midi interface interface.

Surface Presser is intended to allow you control (and observation) of arbitrary backends using any midi device. I originally built it for my Behringer X-Touch One, but because the midi controller is setup entirely in YAML, you can use it with any MIDI Device.

It uses asyncio to asynchronously handle the input/output and translation, there is currently no UI at all.

## Setup Controllers - (MIDI devices)
If you have an already configured device such as:
* Behringer X touch One
All you need to do is include the config for that controller.

If you have a different device, you'll need to make a configuration profile for it. More details are available at [Midi Setup](doc/MIDISetup.md)

There's no reason that surface presser should be limited to MIDI Devices, the design allows it to be used for anything. Likely targets includes stream deck (because I have one) and perhaps other custom/DIY Solutions.


## Setup - external services/libraries

### Pipewire.

Pipewire offers amazing flexiblity at the cost of amazing complexity. I've abstracted away most of the complexity so you can easily control your pipewire devices natively, without using a pulse or alsa abstraction.

example setup:
```yaml
pipewire:
  datamap:
    volume:
      from_function: "int(min(x*96,127))" # scitools function string, where x is from midi (0-127) 
      to_function: "x/96" # scitools function string, where x is from library and return is midi (0-127)
    volume_mapped_example:
      map: # This example map shows the mapping of the db on my fader to midi
        midi:     [0  ,   4,  13,  21, 29,   46,  62,  69,  79, 96, 111, 127]
        pipewire: [-60, -60, -50, -40, -30, -20, -10, -7.9, -5,  0,  +5, +12]
        # The map is interpolated, so you need a minimum two values (0 and 127)
  devices: # Device name map to nice human names
    'ALSA plug-in [vban_desktop]': 'Desktop'
    'vban': 'Desktop'
    'ALSA plug-in [vban_mic_desktop]': 'DeskMic'
```


### Home Assistant.
Here we have your classic home assistant integration, because no project would be complete without it. I haven't made it yet, so the project isn't complete.

```
when there is a home assistant endpoint, the config will be here!
```

## Setup - linking controls and endpoints.
When you link a control to an endpoint, It magically sets up a bidirectional link, so that (if supported) the control reflects the status of the action at the endpoint

The basic idea is as follows:
```yaml
link: # has to be link, this calls the linker
  midid: # ID of midi controller
    control: # named control from midi controller.
      backend: # backend - eg pipewire, virtual, homeassistant, command
        action: item # performs action (eg volume/mute/run - depends on backend) on item (eg: "Headphones")
```
This tells the linker what the control does, and it makes the connections.

### Magic! Virtual devices
As part of the linker, to allow you to do much cooler things than control a single item, You can setup a virtual target that allows you to change the target of a button (but the function remains the same).

A virtual target exposes two additional controls - ``next`` and ``prev`` which cycle forwards and backwards through the list.

The configuration is as follows:
```yaml
link: # This is part of the linker, so is under the link item.
  virtual: # This tells the linker to use 
    volin: # This is the name of the virtual item
      targets: # This is a list of targets that you can cycle through
        - target: 'Wless HFmic' # Name of target in the backend
          text: 'wls HF' # This is the text to display on the screen if configured
          color: magenta # This is the colour to set on the screen (if applicable)
          invert: True # This inverts the screen (if applicable)
        - target: 'DeskMic' 
      system: pipewire # Currently all targets have to be in the same system
      display: # This sets up the display to show what the virtual target is set to.
        xtouch: # This is the midi ID of the device
          scribble_strip_top # This is the screen - in this case it's a special device which addresses the top half of the scribble strip
```
Note that this will do nothing by itself, this needs to be references by linked controls to be functional. eg:
```yaml
link: # linker
  xtouch: # midi ID
    rotary: # Control name
      virtual: # Put virtual here, because that's the backend.
        volume: volin # We define the action here which applies to the item. 
                      # and we give the virtual target name.
    rotarybutton: 
      virtual:
         next: volin # Here we've used the magic 'next' action which cycles the virtual target.
```
What we've done above is use a rotary button that cycles through the different microphones configured in the system, displays the currently selected item, and allows you to adjust the volume up and down. Due to the magic of the linker, when the target changes, the control will change to indicate the level of the new target.


## Running Surface Presser
```
usage: surfacepresser.py [-h] [--config [CONFIG ...]] [--miditest [MIDI Controller]] [--midilist]

Surface Presser - Midi controller interface.

options:
  -h, --help            show this help message and exit
  --config [CONFIG ...]
                        yaml config files
  --miditest [MIDI Controller]
                        test mode - show midi commands only
  --midilist            list MIDI controllers
  ```
The default config file is surfacepresser.yaml

surface presser doesn't accept any input on the console, It will have some logging outputs, but it runs in the background as a control and status translation application.

## The Future?

It's currently pretty horrific to configure, perhaps there could be a nice click and drag GUI. Something where you take a picture of your midi controller and it auto detects buttons, reads the labels, and lets you adjust it, before then allowing you to link it. Close to zero chance of this happening, but you never know.

