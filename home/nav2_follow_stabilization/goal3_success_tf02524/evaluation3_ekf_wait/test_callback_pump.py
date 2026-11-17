"""Exercise installed Humble queue-selection code without ROS or hardware."""
import ast
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).parent/'candidate/follower_diagnostics'))
from callback_pump import CallbackPump


class CallbackPumpTests(unittest.TestCase):
    def executor_class(self):
        path=Path('/opt/ros/humble/local/lib/python3.10/dist-packages/rclpy/executors.py')
        tree=ast.parse(path.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Executor')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='wait_for_ready_callbacks')
        method.returns=None
        for arg in method.args.args:arg.annotation=None
        namespace={}
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
        class QueueExecutor:
            wait_for_ready_callbacks=namespace['wait_for_ready_callbacks']
            def __init__(self):
                self._cb_iter=None;self._last_args=None;self._last_kwargs=None
                self.seen=[];self.added=[];self.removed=[];self.stopped=False
            def _wait_for_ready_callbacks(self,**kwargs):
                # Nine continuously ready subscriptions; IMU was created last.
                for index in range(9):yield index
            def spin_once(self,timeout_sec):
                self.seen.append(self.wait_for_ready_callbacks(timeout_sec=timeout_sec))
            def add_node(self,node):self.added.append(node)
            def remove_node(self,node):self.removed.append(node)
            def shutdown(self,timeout_sec):self.stopped=True
        return QueueExecutor

    def test_old_timeout_alternation_reproduces_tail_starvation(self):
        executor=self.executor_class()()
        for _ in range(50):
            executor.spin_once(timeout_sec=.01)
            for _ in range(6):executor.spin_once(timeout_sec=0.)
        self.assertNotIn(8,executor.seen)

    def test_persistent_pump_services_tail_and_owns_node_once(self):
        node=object();pump=CallbackPump(node,self.executor_class())
        for _ in range(50):pump.spin_once()
        self.assertEqual(pump.executor.seen[:9],list(range(9)))
        self.assertEqual(pump.executor.added,[node])
        pump.close()
        self.assertEqual(pump.executor.removed,[node]);self.assertTrue(pump.executor.stopped)

    def test_ready_batch_survives_one_callback_control_budgets(self):
        pump=CallbackPump(object(),self.executor_class())
        for _ in range(100):pump.spin_once()
        self.assertGreaterEqual(pump.executor.seen.count(8),11)
        pump.close()


if __name__=='__main__':unittest.main()
