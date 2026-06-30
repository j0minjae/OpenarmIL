from openarm_il.sync_buffer import SyncBuffer, TimestampedItem


def test_sync_buffer_returns_approximate_match_for_required_streams():
    buffer = SyncBuffer(required_streams=["joint_states", "chest"], optional_streams=["left_wrist"], tolerance_sec=0.05)
    buffer.add("joint_states", TimestampedItem(timestamp=1.00, data={"q": 1}))
    buffer.add("chest", TimestampedItem(timestamp=1.03, data="image"))
    buffer.add("left_wrist", TimestampedItem(timestamp=1.02, data="wrist"))

    sample = buffer.get_synchronized_sample(1.01)

    assert sample is not None
    assert sample.timestamp == 1.01
    assert sample.items["joint_states"].data == {"q": 1}
    assert sample.items["chest"].data == "image"
    assert sample.items["left_wrist"].data == "wrist"
    assert buffer.dropped_count == 0


def test_sync_buffer_drops_when_required_stream_missing():
    buffer = SyncBuffer(required_streams=["joint_states", "chest"], optional_streams=[], tolerance_sec=0.05)
    buffer.add("joint_states", TimestampedItem(timestamp=1.00, data={"q": 1}))

    sample = buffer.get_synchronized_sample(1.00)

    assert sample is None
    assert buffer.dropped_count == 1


def test_sync_buffer_omits_optional_stream_outside_tolerance():
    buffer = SyncBuffer(required_streams=["joint_states", "chest"], optional_streams=["left_wrist"], tolerance_sec=0.05)
    buffer.add("joint_states", TimestampedItem(timestamp=2.00, data="state"))
    buffer.add("chest", TimestampedItem(timestamp=2.00, data="chest"))
    buffer.add("left_wrist", TimestampedItem(timestamp=3.00, data="late"))

    sample = buffer.get_synchronized_sample(2.00)

    assert sample is not None
    assert "left_wrist" not in sample.items
    assert buffer.optional_missing_count["left_wrist"] == 1
