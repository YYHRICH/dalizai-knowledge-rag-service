from apps.rag_service.app.privacy import hash_identifier, mask_text


def test_mask_text_replaces_common_sensitive_values() -> None:
    text = "用户手机号13800138000，身份证110101199001011234，邮箱a@test.com，车牌粤B12345，订单ORDER-ABC123456"

    masked = mask_text(text)

    assert masked == "用户手机号[PHONE]，身份证[ID_CARD]，邮箱[EMAIL]，车牌[PLATE]，订单[ORDER_ID]"


def test_hash_identifier_is_stable_and_salted() -> None:
    value = hash_identifier("user_001", "salt_a")

    assert value == hash_identifier("user_001", "salt_a")
    assert value != hash_identifier("user_001", "salt_b")
    assert value != "user_001"
    assert hash_identifier(None, "salt_a") is None
    assert hash_identifier("", "salt_a") is None
