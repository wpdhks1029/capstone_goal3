import unittest
from test_reference_wait_operator import OperatorTests


class StartupAlignmentTests(unittest.TestCase):
    flow=OperatorTests.flow

    def held_disarmed(self,f,rows,stage):
        start=next(r for r in rows if r['event']=='startup_alignment_wait_started' and r['stage']==stage)
        end=next(r for r in rows if r['event']=='startup_alignment_wait_resumed' and r['stage']==stage)
        first=(start['ros_ns']-100_000_000_000)/1e9
        last=(end['ros_ns']-100_000_000_000)/1e9
        # JSON timestamps are rounded to ns while the fake clock uses floats.
        # A pre-detection command can share the entry-log instant; the resume
        # command shares the exit-log instant. Check strictly inside the hold.
        held=[e for e in f.events if e[0]=='leader' and first+1e-6<e[2]<last-1e-6]
        self.assertTrue(held)
        self.assertTrue(all(e[1]==0 for e in held))
        self.assertFalse(any(e[0]=='arm' and first<=e[1]<last-1e-6 for e in f.events))
        self.assertEqual(sum(e[0]=='arm' for e in f.events),1)
        return end

    def test_leader_start_alignment_gap_waits_past_old_four_second_limit(self):
        f,rows=self.flow(loss_end=0.,startup_alignment_end=15.)
        end=self.held_disarmed(f,rows,'LEADER_START')
        self.assertGreater(end['waited_s'],4.)
        self.assertTrue(any(e[0]=='envelope' and e[1]['v']>0 for e in f.events))
        self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')

    def test_alignment_gap_immediately_after_start_waits_before_leader_motion(self):
        f,rows=self.flow(loss_end=0.,after_start_alignment_end=15.)
        self.held_disarmed(f,rows,'AFTER_START')
        self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')

    def test_permanent_startup_alignment_loss_never_arms(self):
        f,rows=self.flow(loss_end=0.,startup_alignment_end=1000.)
        self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')
        self.assertFalse(any(e[0]=='arm' for e in f.events))
        self.assertFalse(any(r['event']=='startup_alignment_wait_resumed' for r in rows))

    def test_genuine_sensor_error_is_not_converted_to_alignment_wait(self):
        f,rows=self.flow(loss_end=0.,startup_alignment_end=15.,startup_error='IMU_STALE')
        self.assertEqual(rows[-1]['reason'],'IMU_STALE')
        self.assertFalse(any(e[0]=='arm' for e in f.events))

    def test_pose_change_during_startup_wait_requires_a_new_reference(self):
        f,rows=self.flow(loss_end=0.,startup_alignment_end=15.,startup_pose_shift=.1)
        self.assertEqual(rows[-1]['reason'],'POSE_CHANGED_AFTER_PLANNING')
        self.assertFalse(any(e[0]=='arm' for e in f.events))

    def test_gap_in_final_check_immediately_before_arm_waits_disarmed(self):
        f,rows=self.flow(loss_end=0.,late_startup_alignment_end=15.)
        self.held_disarmed(f,rows,'BEFORE_ARM')
        self.assertEqual(rows[-1]['reason'],'ROS_SHUTDOWN')


if __name__=='__main__':unittest.main()
