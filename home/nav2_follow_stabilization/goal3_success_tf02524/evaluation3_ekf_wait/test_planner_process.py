import ctypes
import multiprocessing
import os
from pathlib import Path
import sys
import time
import unittest
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0,str(Path(__file__).resolve().parent/'candidate/follower_diagnostics'))
from continuous_local_core import route_still_clear


def gil_holding_planner():
    libc=ctypes.PyDLL(None);libc.usleep.argtypes=[ctypes.c_uint]
    libc.usleep(1_400_000)
    return os.getpid()


class PlannerProcessTests(unittest.TestCase):
    def test_planner_gil_stall_does_not_block_parent_loop(self):
        with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn')) as worker:
            future=worker.submit(gil_holding_planner)
            last=time.monotonic();gaps=[];end=last+10.
            while not future.done() and time.monotonic()<end:
                now=time.monotonic();gaps.append(now-last);last=now;time.sleep(.01)
            self.assertNotEqual(future.result(timeout=1.),os.getpid())
            self.assertLess(max(gaps),.3)

    def test_existing_geometry_function_runs_unchanged_in_spawn_worker(self):
        plan={'continuous_path':[(0.,0.,0.),(.01,0.,0.)]}
        with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn')) as worker:
            for points in ([(0.,.55)],[(0.,.42)]):
                self.assertEqual(worker.submit(route_still_clear,plan,points).result(timeout=10.),route_still_clear(plan,points))


if __name__=='__main__':unittest.main()
