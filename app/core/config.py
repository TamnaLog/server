from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "jamkkan-jeju-api"
    environment: str = Field(default="development")
    # 범용 DEBUG 환경변수는 VS Code/Codex 등 외부 도구와 충돌할 수 있으므로
    # 이 애플리케이션 전용 APP_DEBUG만 읽는다.
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    cors_allowed_origins: str = Field(default="http://localhost:3000")

    mysql_host: str = Field(default="localhost")
    mysql_port: int = Field(default=3306)
    mysql_database: str = Field(default="tour")
    mysql_user: str = Field(default="tour")
    mysql_password: str = Field(default="tour_password")
    mysql_ssl_enabled: bool = Field(default=False)

    # Azure Blob Storage (이미지/오디오 업로드)
    azure_storage_connection_string: str = Field(default="")
    azure_storage_container: str = Field(default="media")

    # OpenAI (방명록 오디오 제목 생성)
    openai_api_key: str = Field(default="")
    openai_audio_transcription_model: str = Field(default="gpt-4o-mini-transcribe")
    openai_audio_title_model: str = Field(default="gpt-4o-mini")
    openai_timeout_seconds: float = Field(default=30)

    # OpenAI (여행 마무리 엽서 이미지 생성)
    # 이미지 생성은 오디오 제목 생성보다 오래 걸려서 모델과 타임아웃을 따로 둔다.
    openai_image_generation_model: str = Field(default="gpt-image-2")
    openai_image_timeout_seconds: float = Field(default=120)

    kto_base_url: str = Field(default="https://apis.data.go.kr/B551011/KorService2")
    kto_service_key: str = Field(default="")
    kto_mobile_os: str = Field(default="ETC")
    kto_mobile_app: str = Field(default="tour-api")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )

    @property
    def database_connect_args(self) -> dict[str, object]:
        if not self.mysql_ssl_enabled:
            return {}
        return {"ssl": {"ca": "/etc/ssl/certs/ca-certificates.crt"}}

    @property
    def azure_storage_enabled(self) -> bool:
        """Blob Storage 연결 문자열이 설정돼 있는지."""
        return bool(self.azure_storage_connection_string)

    @property
    def openai_enabled(self) -> bool:
        """OpenAI API 키가 설정돼 있는지. (오디오가 첨부된 방명록 작성에만 필요하다)"""
        return bool(self.openai_api_key)

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
