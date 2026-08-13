import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Talker(Node):
    def __init__(self):
        super().__init__('talker')

        self.declare_parameter('publisher_period', 1.0)
        self.declare_parameter('message_prefix', 'Hello World from Python')

        period = self.get_parameter('publish_period').value
        self._prefix = self.get_parameter('message_prefix').value

        self._pub = self.create_publisher(String, 'chatter', 10)
        self._timer = self.create_timer(period, self._on_timer)
        self._count = 0

        self.get_logger().info(
            f"talker start | period = {period}s | prefix='{self.prefix}' "
            f"| topic = '{self._pub.topic_name}'"
        )

    def _on_timer(self):
        msg = String()
        msg.data - f'{self._prefix}: {self._count}'
        self._pub.publish(msg)
        self.get_logger().info(f'publish -> "{msg.d.ata}"')
        self._count += 1

def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()