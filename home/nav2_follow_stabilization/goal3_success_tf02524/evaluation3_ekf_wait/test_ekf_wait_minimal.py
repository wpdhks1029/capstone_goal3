import unittest
from test_reference_wait_operator import OperatorTests


class EkfWaitTests(unittest.TestCase):
    flow=OperatorTests.flow

    def test_ekf_loss_stops_then_resumes_same_arm_with_fresh_input(self):
        f,rows=self.flow(loss_end=0.,filtered_loss_end=25.)
        start=next(r for r in rows if r['event']=='filtered_input_wait_started')
        end=next(r for r in rows if r['event']=='filtered_input_wait_resumed')
        self.assertGreater(end['waited_s'],14.)
        held=[e[1] for e in f.events if e[0]=='envelope' and start['ros_ns']<=e[1]['stamp_ns']<end['ros_ns']]
        self.assertTrue(held)
        self.assertTrue(all(r['motion']=='STOP' and r['v']==r['w']==0 for r in held))
        self.assertTrue(any(e[0]=='envelope' and e[1]['v']>0 and e[1]['stamp_ns']>end['ros_ns'] for e in f.events))
        self.assertEqual(sum(e[0]=='arm' for e in f.events),1)
        self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')

    def test_permanent_ekf_loss_holds_without_session_timeout(self):
        f,rows=self.flow(loss_end=0.,filtered_loss_end=1000.)
        self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')
        self.assertFalse(any(r['event']=='filtered_input_wait_resumed' for r in rows))
        self.assertTrue(rows[-1]['follower_zero_confirmed'])

    def test_future_ekf_measurement_is_still_rejected(self):
        f,rows=self.flow(loss_end=0.,filtered_loss_end=15.,filtered_future=True)
        self.assertEqual(rows[-1]['reason'],'FILTERED_FUTURE')

    def test_imu_loss_during_ekf_wait_still_faults(self):
        f,rows=self.flow(loss_end=0.,filtered_loss_end=1000.,imu_loss_end=1000.)
        self.assertEqual(rows[-1]['reason'],'IMU_STALE')

    def test_reference_loss_overlapping_ekf_wait_requires_both_to_recover(self):
        f,rows=self.flow(loss_end=35.,filtered_loss_end=25.)
        filtered_end=next(r for r in rows if r['event']=='filtered_input_wait_resumed')
        reference_end=next(r for r in rows if r['event']=='reference_wait_resumed')
        self.assertGreater(reference_end['ros_ns'],filtered_end['ros_ns'])
        held=[e[1] for e in f.events if e[0]=='envelope' and filtered_end['ros_ns']<=e[1]['stamp_ns']<reference_end['ros_ns']]
        self.assertTrue(held);self.assertTrue(all(e['motion']=='STOP' for e in held))
        self.assertEqual(sum(e[0]=='arm' for e in f.events),1)


if __name__=='__main__':unittest.main()
