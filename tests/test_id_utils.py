from core.id_utils import next_prefixed_id


def test_next_prefixed_id_basic_sequence():
    rows = [{"id": "A001"}, {"id": "A003"}, {"id": "A002"}]
    assert next_prefixed_id(rows, prefix="A", width=3) == "A004"


def test_next_prefixed_id_ignores_invalid_values():
    rows = [{"id": "X999"}, {"id": "AAB"}, {"id": ""}, {}]
    assert next_prefixed_id(rows, prefix="A", width=3) == "A001"
