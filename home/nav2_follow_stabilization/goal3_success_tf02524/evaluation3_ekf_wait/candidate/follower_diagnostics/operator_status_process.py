"""Isolate display-only DDS writes; owns no hardware or command publisher."""
import sys
import tempfile
import shutil
from pathlib import Path


class OperatorStatusPublisher:
    def __init__(self, *, serialize=None, target=None):
        driver = Path(__file__).resolve().parents[3] / 'transport_driver'
        if str(driver) not in sys.path:
            sys.path.append(str(driver))
        from isolated_telemetry import PublisherProcess
        if serialize is None:
            from rclpy.serialization import serialize_message
            serialize = serialize_message
        self.serialize = serialize
        self.directory = Path(tempfile.mkdtemp(prefix='convoy-operator-status-'))
        try:
            options = {} if target is None else {'target': target}
            self.worker = PublisherProcess(self.directory/'status.slot',
                '/follower/local_avoidance/status', 'std_msgs/msg/String', 1,
                'follower_operator_status_telemetry', **options)
        except BaseException:
            shutil.rmtree(self.directory)
            raise

    def publish(self, message):
        # Latest-only, nonblocking IPC. Original source timestamps stay intact.
        self.worker.offer(bytes(self.serialize(message)))

    def close(self):
        self.worker.close()
        shutil.rmtree(self.directory)
