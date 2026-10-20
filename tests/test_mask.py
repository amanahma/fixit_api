from app.logging_setup import mask_phones


def test_mask_phone() -> None:
    assert mask_phones("call 9876543210 now") == "call 98xxxxxx10 now"
