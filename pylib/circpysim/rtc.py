
import datetime
import circpysim_base

class RTC:
    def __init__(self):
        pass

    def get_date(self): return datetime.datetime.now()
    
    def set_date(self, newdate):
        circpysim_base.log(f'set rtc time to: {newdate}')

    def del_date(self): pass

    datetiem = property(get_date, set_date, del_date)

