"""JWT: roundtrip, проверка типа токена, отклонение мусора."""

import pytest

from app.core.security.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_access_roundtrip() -> None:
    assert decode_token(create_access_token(42), "access") == 42


def test_refresh_roundtrip() -> None:
    assert decode_token(create_refresh_token(7), "refresh") == 7


def test_wrong_token_type() -> None:
    access = create_access_token(1)
    with pytest.raises(TokenError):
        decode_token(access, "refresh")


def test_invalid_token() -> None:
    with pytest.raises(TokenError):
        decode_token("garbage.token.value", "access")
