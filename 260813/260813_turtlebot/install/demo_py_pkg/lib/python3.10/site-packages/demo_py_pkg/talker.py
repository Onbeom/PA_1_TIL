#!/usr/bin/env python3
"""std_msgs/String 퍼블리셔.

파라미터
    publish_period (double) : 발행 주기 [s]
    message_prefix (string) : 메시지 앞에 붙일 문구

토픽
    chatter (std_msgs/String) : 발행. launch 에서 remapping 된다.
"""

import rclpy
from rclpy.node import Node
# from std_msgs.msg import String

import random
from geometry_msgs.msg import Twist


class Talker(Node):

    vel = 0.0
    ang = 0.0

    def __init__(self):
        super().__init__('talker')

        # 파라미터는 반드시 declare 한 뒤에 읽는다.
        # launch 의 parameters=[...] 나 params.yaml 이 이 기본값을 덮어쓴다.
        self.declare_parameter('publish_period', 1.0)
        # self.declare_parameter('message_prefix', 'Hello from Python')

        period = self.get_parameter('publish_period').value
        # self._prefix = self.get_parameter('message_prefix').value

        # 코드에는 상대 토픽명만 쓴다. 네임스페이스와 remapping 은 launch 가 정한다.
        # self._pub = self.create_publisher(String, 'chatter', 10)
        # self._timer = self.create_timer(period, self._on_timer)
        # self._count = 0

        self._pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self._timer = self.create_timer(period, self._on_timer)

        self.get_logger().info(
            # f"talker 시작 | period={period}s | prefix='{self._prefix}' "
            # f"| topic='{self._pub.topic_name}'"
            f"talker(WASD Controller) Start|period={period}s|topic='{self._pub.topic_name}'"
        )

    def _on_timer(self):
        # msg = String()
        # msg.data = f'{self._prefix}: {self._count}'
        msg = Twist()
        current_key = random.choice(['w'])

        if current_key == 'w':
            msg.linear.x = self.vel
            self.vel += 0.5
            msg.angular.z = 0.0
        elif current_key == 's':
                msg.linear.x = self.vel
                self.vel -= 0.5
                msg.angular.z = 0.0
        elif current_key == 'a':
                msg.linear.x = - 0.0
                msg.angular.z = self.ang
                self.ang += 0.5
        elif current_key == 'd':
                msg.linear.x = 0.0
                msg.angular.z = self.ang
                self.ang -= 0.5

        self._pub.publish(msg)
        self.get_logger().info(f'Key Input : [{current_key}] -> publish cmd_vel (linear : {msg.linear.x}, angular : {msg.angular.z})')
        # self.get_logger().info(f'publish -> "{msg.data}"')
        # self._count += 1


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
