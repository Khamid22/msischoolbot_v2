from werkzeug.security import generate_password_hash

from backend.modules.domains.identity.passwords import verify_password_hash
from backend.modules.domains.identity.service import verify_account_password


def test_verify_password_hash_valid_password_returns_true():
    password_hash = generate_password_hash("correct-password")

    assert verify_password_hash(password_hash, "correct-password") is True


def test_verify_password_hash_wrong_password_returns_false():
    password_hash = generate_password_hash("correct-password")

    assert verify_password_hash(password_hash, "wrong-password") is False


def test_verify_password_hash_blank_hash_returns_false():
    assert verify_password_hash("   ", "correct-password") is False


def test_verify_password_hash_none_hash_returns_false():
    assert verify_password_hash(None, "correct-password") is False


def test_verify_password_hash_invalid_hash_returns_false():
    assert verify_password_hash("not-a-valid-werkzeug-hash", "correct-password") is False


def test_account_auth_verify_account_password_uses_core_hash_verifier():
    password_hash = generate_password_hash("correct-password")
    account = {"password_hash": password_hash}

    assert verify_account_password(account, "correct-password") is True
    assert verify_account_password(account, "wrong-password") is False
