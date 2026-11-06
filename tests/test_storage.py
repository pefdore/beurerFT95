from ft95.storage import MeasurementStore, load_history
from ft95.decode import make_measurement


def test_save_and_reload(tmp_path):
    store = MeasurementStore(str(tmp_path / "m.csv"), str(tmp_path / "m.jsonl"))
    store.save(make_measurement(38.2, b"ab", "test"))
    store.save(make_measurement(37.9, b"cd", "test"))
    hist = load_history(str(tmp_path / "m.jsonl"))
    assert len(hist) == 2
    assert hist[-1].temperature_c == 37.9
