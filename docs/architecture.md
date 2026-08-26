# 아키텍처 문서

이 문서는 현재 개발용 백엔드 서버가 어떤 구조로 동작하는지 설명합니다. 프론트엔드 개발자는 API 주소와 요청 흐름을 확인할 때, 백엔드 개발자는 배포 구조와 환경변수 위치를 확인할 때 참고하면 됩니다.

## 전체 구조

현재 서버는 FastAPI 애플리케이션을 Docker 이미지로 만들고, Azure App Service에서 그 이미지를 실행하는 구조입니다.

```text
Next.js Frontend
        |
        | HTTPS API 요청
        v
Azure App Service
  jankkan-jeju
        |
        | Docker 이미지 실행
        v
Azure Container Registry
  jankkanjejuacr.azurecr.io/jamkkan-jeju-api
        |
        | TLS로 MySQL 연결
        v
Azure Database for MySQL Flexible Server
  jankkan-jeju-mysql
```

## 요청 흐름

프론트엔드가 API를 호출하면 요청은 다음 순서로 처리됩니다.

1. Next.js 앱이 `https://jankkan-jeju.azurewebsites.net`로 HTTP 요청을 보냅니다.
2. Azure App Service가 요청을 받습니다.
3. App Service 안에서 실행 중인 Docker 컨테이너가 FastAPI 서버를 처리합니다.
4. FastAPI가 필요한 경우 Azure MySQL에 연결합니다.
5. FastAPI가 JSON 응답을 반환합니다.

개발용 서버 URL:

```text
https://jankkan-jeju.azurewebsites.net
```

기본 확인 API:

```text
GET /health
GET /health/db
```

## 애플리케이션 구조

FastAPI 진입점은 다음 파일입니다.

```text
app/main.py
```

설정값은 다음 파일에서 환경변수로 읽습니다.

```text
app/core/config.py
```

DB 연결은 다음 파일에서 관리합니다.

```text
app/core/database.py
```

## Docker 구조

운영/배포용 컨테이너는 `Dockerfile`로 빌드합니다.

```text
Dockerfile
```

컨테이너는 내부 포트 `8000`에서 FastAPI를 실행합니다. Azure App Service도 `WEBSITES_PORT=8000` 설정으로 이 포트를 바라봅니다.

실행 방식:

```text
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2
```

## Azure 리소스

현재 개발용 리소스는 다음과 같습니다.

```text
Resource Group: jankkan-jeju-rg
App Service: jankkan-jeju
App Service Plan: jankkan-jeju-plan
Container Registry: jankkanjejuacr
MySQL Server: jankkan-jeju-mysql
Database: tour
```

App Service 이름에 오타가 있지만 현재 개발용 서버로 사용 중입니다. 운영 서버를 새로 만들 때는 원하는 이름으로 다시 생성하면 됩니다.

## 이미지 저장소

Docker 이미지는 Azure Container Registry에 저장됩니다.

```text
jankkanjejuacr.azurecr.io/jamkkan-jeju-api
```

GitHub Actions는 배포할 때 두 가지 태그를 push합니다.

```text
jamkkan-jeju-api:${GITHUB_SHA}
jamkkan-jeju-api:latest
```

실제 App Service 배포에는 커밋 SHA 태그가 사용됩니다. `latest`는 사람이 확인하거나 수동 배포할 때 참고하기 위한 보조 태그입니다.

## 데이터베이스 연결

DB는 Azure Database for MySQL Flexible Server를 사용합니다.

```text
jankkan-jeju-mysql.mysql.database.azure.com
```

Azure MySQL은 보안 연결을 요구하므로 배포 환경에서는 TLS 연결을 사용합니다.

관련 환경변수:

```env
MYSQL_HOST=jankkan-jeju-mysql.mysql.database.azure.com
MYSQL_PORT=3306
MYSQL_DATABASE=tour
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_SSL_ENABLED=true
```

로컬 Docker Compose에서는 MySQL 컨테이너를 직접 띄우기 때문에 `MYSQL_SSL_ENABLED=false`를 사용합니다.

## 파일 저장소 (Azure Blob Storage)

사용자가 올린 사진/음성 파일은 DB에 URL만 저장하고 실제 파일은 Blob Storage에 둡니다.

```text
Storage Account: jamkkanjejustorage
Blob Endpoint:   https://jamkkanjejustorage.blob.core.windows.net/
```

업로드 코드는 다음 파일에 있습니다.

```text
app/services/blob_storage.py
```

관련 환경변수:

```env
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=jamkkanjejustorage;AccountKey=...;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER=media
```

연결 문자열에는 계정 키가 들어 있으므로 Git에 올리지 않고 환경변수로만 주입합니다.
컨테이너는 첫 업로드 시 없으면 자동으로 생성합니다.

## 비밀값 관리

비밀번호나 외부 API 키는 Git에 올리지 않습니다.

로컬 개발:

```text
.env
```

Azure 배포 서버:

```text
Azure App Service > Environment variables
```

GitHub Actions:

```text
GitHub Repository > Settings > Secrets and variables > Actions
```

현재 GitHub Actions에는 배포에 필요한 ACR/App Service 인증값만 들어갑니다. DB 비밀번호와 외부 API 키는 App Service 환경변수에 남아 있습니다.

## 자동 배포 구조

자동 배포 파일:

```text
.github/workflows/deploy-dev.yml
```

자동 배포 흐름:

1. `dev` 브랜치에 push합니다.
2. GitHub Actions가 실행됩니다.
3. Docker 이미지를 빌드합니다.
4. 이미지를 Azure Container Registry에 push합니다.
5. Azure App Service가 새 이미지를 배포합니다.
6. 배포 후 개발용 API 서버에 변경사항이 반영됩니다.

필요한 GitHub Secrets:

```text
ACR_USERNAME
ACR_PASSWORD
AZURE_WEBAPP_PUBLISH_PROFILE
```

## 운영 서버 확장 계획

현재 서버는 개발용입니다. 운영 서버를 만들 때는 개발 리소스와 분리하는 것이 좋습니다.

권장 예시:

```text
dev App Service: jamkkan-jeju-dev
prod App Service: jamkkan-jeju
```

운영 서버를 만들 때는 DB, App Service, GitHub Actions workflow도 dev/prod로 분리하면 됩니다.

권장 브랜치 전략:

```text
dev  -> 개발 서버 자동 배포
main -> 운영 서버 자동 배포 예정
```

현재 구성된 workflow는 개발 서버용 `deploy-dev.yml`뿐입니다. 운영 서버가 준비되면 `deploy-prod.yml`을 추가해서 `main` 브랜치 push에 연결합니다.
