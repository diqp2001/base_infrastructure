from datetime import datetime, time, timedelta
from typing import  Optional, Callable

class TimeOrder:
    """
    Represents an order that should be executed at a specific time.
    
    Attributes:
        execute_time: The datetime when the order should be executed.
        action: A callable to execute the order (e.g., a function that places the order).
        executed: Whether the order has already been executed.
        repeat_interval: Optional timedelta for repeated execution.
    """
    
    def __init__(
        self,
        execute_time: datetime,
        action: Callable,
        repeat_interval: Optional[timedelta] = None
    ):
        self.execute_time = execute_time
        self.action = action
        self.executed = False
        self.repeat_interval = repeat_interval

    def check_and_execute(self, current_time: datetime):
        """
        Checks if the order should be executed at the current time.
        Executes the order if the time has passed.
        """
        if not self.executed and current_time >= self.execute_time:
            self.action()
            self.executed = True
            # Reschedule if repeat_interval is set
            if self.repeat_interval:
                self.execute_time += self.repeat_interval
                self.executed = False
