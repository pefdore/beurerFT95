from ft95.decode import decode_health_thermometer, decode_heuristic, decode_ieee11073_32bit, make_measurement
from ft95.ble import looks_like_ft95


def test_ieee11073():
    # 37.5 °C = mantisse 37500, exposant -3
    assert decode_ieee11073_32bit(bytes([0x7C, 0x92, 0x00, 0xFD])) == 37.5


def test_health_thermometer_celsius():
    # flags=0x00 + 37.5 IEEE-11073
    assert decode_health_thermometer(bytes([0x00, 0x7C, 0x92, 0x00, 0xFD])) == 37.5


def test_health_thermometer_fahrenheit():
    # flags=0x01, 99.5 °F : mantisse 995, exposant -1
    v = decode_health_thermometer(bytes([0x01, 0xE3, 0x03, 0xFF]))
    assert abs(v - 37.5) < 0.01


def test_heuristic():
    assert decode_heuristic(bytes([0xD8, 0x0E, 0xAE])) == 38.0  # 3800/100


def test_name_detection():
    assert looks_like_ft95("FT95")
    assert looks_like_ft95("Beurer FT95")
    assert not looks_like_ft95("MI_SCALE")


def test_make_measurement():
    m = make_measurement(38.15, b"\x01", "test")
    assert m.temperature_c == 38.2 or m.temperature_c == 38.1
    assert m.source == "test"
