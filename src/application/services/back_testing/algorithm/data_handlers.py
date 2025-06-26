class Slice:
    def __init__(self, data=None):
        self.data = data or {}

class TradeBars(Slice):
    pass

class QuoteBars(Slice):
    pass
