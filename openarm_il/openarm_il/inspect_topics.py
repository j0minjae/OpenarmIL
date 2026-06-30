"""ROS2 topic inspector for expected OpenArmIL recording streams."""

from __future__ import annotations

import argparse
from pathlib import Path

from openarm_il.config import load_topic_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect expected OpenArmIL ROS2 topics.")
    parser.add_argument("--topics-config", default=None)
    args = parser.parse_args()

    try:
        import rclpy
        from rclpy.node import Node
    except Exception as exc:
        raise SystemExit(f"rclpy is required for topic inspection: {exc}")

    topics = load_topic_config(Path(args.topics_config) if args.topics_config else None)
    expected = {"joint_states": topics.joint_states}
    expected.update({f"camera.{name}": topic for name, topic in topics.cameras.items()})
    expected.update({f"action.{name}": topic for name, topic in topics.actions.items()})

    rclpy.init()
    node = Node("openarm_il_topic_inspector")
    try:
        available = {name: types for name, types in node.get_topic_names_and_types()}
        missing_required = []
        for label, topic in expected.items():
            types = available.get(topic, [])
            status = "OK" if types else "MISSING"
            print(f"{status:7s} {label:24s} {topic:60s} types={types or ['unknown']} rate_hz=not_measured last_stamp=not_measured")
            if label in {"joint_states", "camera.chest"} and not types:
                missing_required.append(topic)
        if missing_required:
            print("missing required topics: " + ", ".join(missing_required))
            return 1
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
