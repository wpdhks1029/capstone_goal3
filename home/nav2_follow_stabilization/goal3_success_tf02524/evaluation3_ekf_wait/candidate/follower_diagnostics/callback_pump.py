"""Keep a single executor and ready-callback iterator across control cycles."""


class CallbackPump:
    def __init__(self,node,executor_factory=None):
        if executor_factory is None:
            from rclpy.executors import SingleThreadedExecutor
            executor_factory=SingleThreadedExecutor
        self.executor=executor_factory()
        self.node=node
        self.executor.add_node(node)

    def spin_once(self):
        # Humble replaces its ready iterator if timeout kwargs change. Using
        # the same arguments lets subscriptions at the end of a ready batch
        # run even when the caller's time budget cuts a drain short.
        self.executor.spin_once(timeout_sec=.01)

    def close(self):
        self.executor.remove_node(self.node)
        self.executor.shutdown(timeout_sec=0.)
