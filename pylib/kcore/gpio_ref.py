'''Reference for the several different names given to Raspberry PI pins.'''

from dataclasses import dataclass

@dataclass
class PinMap:
    bcm_name: str
    bcm: int
    board: int

PIN_MAPPINGS = {
    'raspberry_pi': [
        #      name     bcm#   board#
        PinMap('D0',    0,     None),
        PinMap('D1',    1,     None),
        PinMap('3v',    None,  1),
        PinMap('5v',    None,  2),
        PinMap('D2',    2,     3),
        PinMap('SDA',   2,     3),
        PinMap('5v#2',  None,  4),
        PinMap('D3',    3,     5),
        PinMap('SCL',   3,     5),
        PinMap('gnd',   None,  6),
        PinMap('D4',    4,     7),
        PinMap('D14',   14,    8),
        PinMap('TX',    14,    8),
        PinMap('TXD',   14,    8),
        PinMap('gnd#2', None,  9),
        PinMap('D15',   15,    10),
        PinMap('RX',    15,    10),
        PinMap('RXD',   15,    10),
        PinMap('D17',   17,    11),
        PinMap('D18',   18,    12),
        PinMap('D27',   27,    13),
        PinMap('gnd#3', None,  14),
        PinMap('D22',   22,    15),
        PinMap('D23',   23,    16),
        PinMap('3v#2',  None,  17),
        PinMap('D24',   24,    18),
        PinMap('D10',   10,    19),
        PinMap('MOSI',  10,    19),
        PinMap('gnd#4', None,  20),
        PinMap('D9',    9,     21),
        PinMap('MISO',  9,     21),
        PinMap('D25',   25,    22),
        PinMap('D11',   11,    23),
        PinMap('SCK',   11,    23),
        PinMap('SCLK',  11,    23),
        PinMap('CE0',   8,     24),
        PinMap('D8',    8,     24),
        PinMap('gnd#5', None,  25),
        PinMap('CE1',   7,     26),
        PinMap('D7',    7,     26),
        PinMap('id_sd', None,  27),
        PinMap('id_sc', None,  28),
        PinMap('D5',    5,     29),
        PinMap('gnd#6', None,  30),
        PinMap('D6',    6,     31),
        PinMap('D12',   12,    32),
        PinMap('D13',   13,    33),
        PinMap('gnd#7', None,  34),
        PinMap('D19',   19,    35),
        PinMap('MISO_1',19,    35),
        PinMap('D16',   16,    36),
        PinMap('D26',   26,    37),
        PinMap('D20',   20,    38),
        PinMap('MOSI_1',20,    38),
        PinMap('gnd#7', None,  39),
        PinMap('D21',   21,    40),
        PinMap('SCK_1', 21,    40),
        PinMap('SCLK_1',21,    40) ],
    }
