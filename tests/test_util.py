from civic_redressal.utils.util import sanitize_text


def test_sanitize_text_handles_non_string_values():
    assert sanitize_text(3.14) == ""
    assert sanitize_text(None) == ""
    assert sanitize_text({"foo": "bar"}) == ""
