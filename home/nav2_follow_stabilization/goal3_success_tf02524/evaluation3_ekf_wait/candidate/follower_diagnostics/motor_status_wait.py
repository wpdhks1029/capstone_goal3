"""Unbounded zero-speed operator wait; never rearms or clears a driver fault."""
from reference_wait import ReferenceWait

class MotorStatusWait(ReferenceWait):
    def ready_status(self,now,mono,state):
        stamp=state.get('status_ros_ns');feedback=state.get('valid_feedback')
        if (type(stamp) is not int or not 0<=(now-stamp)/1e9<=.3
                or type(feedback) is not int or feedback<=0):
            self.enter(mono,invalid=True);return False
        stopped=(state.get('measured_rpm')==[0,0]
                 and state.get('zero_feedback_samples',0)>=3)
        return self.ready(mono,{'status':stamp,'feedback':feedback},stopped)
