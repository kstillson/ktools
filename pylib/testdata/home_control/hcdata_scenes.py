
SCENES = {
    'trivial1'  : [ 'device1' ],
    'trivial2'  : [ 'device1:off' ],
    'scene1'    : [ 'device1', 'device2' ],
    'scene2'    : [ 'scene1', 'wildq:off' ],
    'scene2:x'  : [ 'scene1:x1', 'wildq:off', 'wild1-2' ],
    'scene3'    : [ 'device1', 'deviceZ' ],
}


def init(devices, scenes):
    scenes.update(SCENES)
    return devices, scenes
