import ctypes
import os
import sys
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'candidate/follower_diagnostics'))
sys.path.append(str(ROOT.parent/'transport_driver'))
from operator_status_process import OperatorStatusPublisher
from isolated_telemetry import LatestSlot


def blocked_status(path,parent_pid,*args):
    slot=LatestSlot(path)
    try:
        slot.mark(ready=True)
        while os.getppid()==parent_pid:
            meta=slot.metadata()
            if meta and meta['stop']:break
            packet=slot.snapshot(0)
            if packet is None:time.sleep(.003);continue
            slot.mark(publish_started_mono=time.monotonic())
            libc=ctypes.PyDLL(None)
            libc.usleep.argtypes=[ctypes.c_uint]
            libc.usleep(1_400_000)
            slot.mark(published=1,publish_started_mono=0.)
            break
    finally:slot.close()


class Tests(unittest.TestCase):
    def test_status_dds_gil_stall_cannot_block_operator_thread(self):
        publisher=OperatorStatusPublisher(serialize=lambda m:m,target=blocked_status)
        try:
            publisher.publish(b'block')
            end=time.monotonic()+3.
            while not publisher.worker.stats().get('publish_started_mono'):
                if time.monotonic()>end:self.fail('child did not start test publish')
                # Latest-only IPC may intentionally drop a contended offer.
                # Match periodic telemetry rather than assuming first delivery.
                publisher.publish(b'block')
                time.sleep(.005)
            start=time.monotonic()
            for _ in range(100):publisher.publish(b'latest')
            self.assertLess(time.monotonic()-start,.1)
            self.assertEqual(publisher.worker.stats()['published'],0)
            self.assertEqual(publisher.worker.slot.snapshot(0)[1],b'latest')
        finally:publisher.close()


if __name__=='__main__':unittest.main()
