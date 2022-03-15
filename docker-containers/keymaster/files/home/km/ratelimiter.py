
import time


class RateLimiter(object):
    
    def __init__(self, time_per_key):
        self.time_per_key = time_per_key
        self.reset()

    def reset(self):
        self.key_to_last_time = {}

    def check(self, key):
        last_time = self.key_to_last_time.get(key, 0)
        
        # If we haven't seen this key before, register it's last seen time
        # as now, and return that the rate limit passes.
        if not last_time:
            self.key_to_last_time[key] = time.time()
            return True

        # If the last success time is less than our limit, deny the check,
        # and leave the last success time alone.
        now = time.time()
        if now - last_time < self.time_per_key:
            return False

        # Otherwise the last time we saw this was past our rate limit,
        # so update last success time to now and return that the limit passes.
        self.key_to_last_time[key] = now
        return True

