#!/usr/bin/python3

import datetime, os
import data


def main():
    default_time = int(datetime.datetime(2022, 1, 1, 0, 0).timestamp())

    dir = os.path.dirname(data.PARTITION_STATE_FILENAME)
    if not os.path.isdir(dir): os.mkdir(dir)
    
    with open(data.PARTITION_STATE_FILENAME, 'w') as f: pass
    with data.saved_list(data.PARTITION_STATE) as pdata:
        pdata.append(data.PartitionState('default', 'arm-auto', default_time))
        pdata.append(data.PartitionState('safe', 'arm-away', default_time))

    with open(data.TOUCH_DATA_FILENAME, 'w') as f: pass
    with data.saved_list(data.TOUCH_DATA) as tdata:
        tdata.append(data.TouchData('ken', default_time, 'away'))
        tdata.append(data.TouchData('dad', default_time, 'away'))
        for tl in data.TRIGGER_LOOKUPS:
            if not tl.friendly_name: continue
            trigger_name = tl.trigger_regex.translate({ord(c): None for c in '.*$'})
            tdata.append(data.TouchData(trigger_name, default_time))
            

if __name__ == '__main__':
    main()
    
