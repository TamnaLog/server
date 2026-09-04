"""애플리케이션 환경변수 이름 검증."""

from app.core.config import Settings


def test_범용_DEBUG를_무시하고_APP_DEBUG를_사용한다(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.setenv("APP_DEBUG", "false")

    settings = Settings(_env_file=None)

    assert settings.debug is False


def test_APP_DEBUG_true를_boolean으로_읽는다(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.setenv("APP_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.debug is True
