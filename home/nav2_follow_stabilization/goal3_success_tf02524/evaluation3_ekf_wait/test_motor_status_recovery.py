import unittest
from test_reference_wait_operator import OperatorTests


class StatusRecoveryTests(unittest.TestCase):
    flow=OperatorTests.flow

    def test_status_delay_holds_zero_and_resumes_same_arm(self):
        f,rows=self.flow(loss_end=0.,status_loss_end=25.)
        start=next(r for r in rows if r['event']=='motor_status_wait_started')
        end=next(r for r in rows if r['event']=='motor_status_wait_resumed')
        held=[e[1] for e in f.events if e[0]=='envelope' and start['ros_ns']<=e[1]['stamp_ns']<end['ros_ns']]
        self.assertTrue(held);self.assertTrue(all(e['motion']=='STOP' and e['v']==e['w']==0 for e in held))
        self.assertGreater(end['waited_s'],14.)
        self.assertTrue(any(e[0]=='envelope' and e[1]['stamp_ns']>end['ros_ns'] and e[1]['v']>0 for e in f.events))
        self.assertEqual(sum(e[0]=='arm' for e in f.events),1)

    def test_permanent_status_loss_and_old_stamps_never_resume(self):
        for end,kind in ((1000.,None),(15.,'stale_stamp')):
            with self.subTest(kind=kind):
                f,rows=self.flow(loss_end=0.,status_loss_end=end,status_return=kind)
                self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')
                self.assertFalse(any(r['event']=='motor_status_wait_resumed' for r in rows))

    def test_hardware_fault_and_new_epoch_still_abort(self):
        for kind,reason in (('fault','MOTOR_FAULT_OR_FEEDBACK_STALE'),('restart','SESSION_CHANGED')):
            with self.subTest(kind=kind):
                f,rows=self.flow(loss_end=0.,status_loss_end=15.,status_return=kind)
                self.assertEqual(rows[-1]['reason'],reason)
                self.assertEqual(sum(e[0]=='arm' for e in f.events),1)

    def test_isolated_io_entrypoint_keeps_commands_and_closes_display_process(self):
        f,rows=self.flow(loss_end=0.,isolated_io=True)
        self.assertTrue(rows[-1]['isolated_io']);self.assertTrue(f.display_process_closed)
        self.assertTrue(any(e[0]=='envelope' and e[1]['v']>0 for e in f.events))


if __name__=='__main__':unittest.main()
