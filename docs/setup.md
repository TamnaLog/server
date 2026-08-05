# 세팅 가이드

이 문서는 새 개발자가 로컬에서 백엔드 서버를 실행하고, GitHub Actions를 통해 Azure 개발 서버에 배포하는 방법을 설명합니다.

## 준비물

로컬 개발과 배포 작업을 하려면 아래 도구가 필요합니다.

```text
Docker Desktop
Azure CLI
GitHub CLI
Python 3.12
```

로그인이 필요한 경우:

```powershell
az login
gh auth login
```

Docker Desktop은 실행 중이어야 합니다. Docker가 꺼져 있으면 로컬 MySQL/FastAPI 컨테이너 실행과 Docker 이미지 빌드가 실패합니다.

## 로컬 환경변수 만들기

처음 프로젝트를 받은 뒤 `.env.example`을 복사해서 `.env`를 만듭니다.

```powershell
Copy-Item .env.example .env
```

`.env`는 개인 로컬 설정 파일입니다. 실제 비밀번호나 API 키가 들어갈 수 있으므로 Git에 올리면 안 됩니다.

현재 `.gitignore`에서 `.env`는 제외되어 있습니다.

## 로컬 서버 실행

FastAPI와 MySQL을 Docker Compose로 함께 실행합니다.

```powershell
docker compose -f docker-compose.dev.yml up --build
```

실행 후 아래 주소를 확인합니다.

```text
API 서버: http://localhost:8000
Swagger UI: http://localhost:8000/docs
Health: http://localhost:8000/health
DB Health: http://localhost:8000/health/db
```

정상이라면 `/health`는 다음처럼 응답합니다.

```json
{"status":"ok","environment":"development"}
```

DB 연결까지 정상이라면 `/health/db`는 다음처럼 응답합니다.

```json
{"status":"ok"}
```

## 로컬 DB 설정

로컬 Docker Compose에서는 MySQL 컨테이너 이름이 `mysql`입니다. 따라서 로컬 `.env`의 DB 설정은 아래처럼 둡니다.

```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=tour
MYSQL_USER=tour
MYSQL_PASSWORD=tour_password
MYSQL_SSL_ENABLED=false
```

Azure MySQL은 TLS를 사용하지만, 로컬 MySQL 컨테이너는 TLS 없이 연결하므로 `MYSQL_SSL_ENABLED=false`가 맞습니다.

## 외부 API 키 설정

외부 API를 로컬에서 테스트하려면 `.env`에 실제 키를 넣어야 합니다.

```env
KTO_BASE_URL=https://apis.data.go.kr/B551011/KorService2
KTO_SERVICE_KEY=put-your-real-key-here
KTO_MOBILE_OS=ETC
KTO_MOBILE_APP=tour-api
```

키를 Git에 올리지 않도록 주의합니다. `.env.example`과 `.env.production.example`에는 실제 키 대신 placeholder만 둡니다.

## 개발용 Azure 서버

현재 개발용 API 서버는 아래 주소입니다.

```text
https://jankkan-jeju.azurewebsites.net
```

프론트엔드에서는 다음 환경변수로 API 서버 주소를 관리하는 것을 권장합니다.

```env
NEXT_PUBLIC_API_BASE_URL=https://jankkan-jeju.azurewebsites.net
```

프론트엔드에서 API 호출 예시:

```ts
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const response = await fetch(`${apiBaseUrl}/health`);
```

## 수동 Docker 배포

GitHub Actions를 쓰지 않고 직접 배포해야 할 때만 사용합니다.

```powershell
docker build --tag jankkanjejuacr.azurecr.io/jamkkan-jeju-api:latest .
docker push jankkanjejuacr.azurecr.io/jamkkan-jeju-api:latest
az webapp restart --resource-group jankkan-jeju-rg --name jankkan-jeju
```

이 방식은 로컬 PC에서 Docker 이미지를 직접 빌드하고 ACR에 push합니다. Azure for Students 환경에서는 ACR 원격 빌드가 제한될 수 있으므로 로컬 Docker 빌드 방식을 사용합니다.

## 자동 배포

GitHub Actions 자동 배포가 설정되어 있습니다.

워크플로 파일:

```text
.github/workflows/deploy-dev.yml
```

배포가 실행되는 경우:

```text
dev 브랜치 push
GitHub Actions 수동 실행
```

배포 흐름:

```text
git push
-> GitHub Actions 실행
-> Docker 이미지 빌드
-> Azure Container Registry에 이미지 push
-> Azure App Service에 새 이미지 배포
```

## GitHub Secrets

자동 배포를 위해 GitHub 저장소에 아래 secrets가 필요합니다.

```text
ACR_USERNAME
ACR_PASSWORD
AZURE_WEBAPP_PUBLISH_PROFILE
```

현재 저장소에는 이미 설정되어 있습니다.

DB 비밀번호, 외부 API 키 같은 애플리케이션 실행 비밀값은 GitHub Actions에 넣지 않고 Azure App Service 환경변수에 저장합니다.

## 브랜치 전략

개발 서버와 운영 서버를 분리하기 위해 브랜치도 분리합니다.

```text
dev  -> 개발 서버 배포
main -> 운영 서버 배포 예정
```

현재는 개발 서버만 배포되어 있으므로 `dev` 브랜치에 push될 때만 `jankkan-jeju` 개발 서버로 자동 배포됩니다. 운영 서버를 만들면 `main` 브랜치용 `deploy-prod.yml`을 별도로 추가합니다.

## Azure App Service 환경변수

Azure Portal에서 확인 위치:

```text
App Service > jankkan-jeju > Environment variables
```

필수 설정:

```env
WEBSITES_PORT=8000
APP_NAME=jamkkan-jeju-api
ENVIRONMENT=production
DEBUG=false
MYSQL_HOST=jankkan-jeju-mysql.mysql.database.azure.com
MYSQL_PORT=3306
MYSQL_DATABASE=tour
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_SSL_ENABLED=true
```

## 배포 후 확인

배포가 끝나면 아래 주소를 확인합니다.

```text
https://jankkan-jeju.azurewebsites.net/health
https://jankkan-jeju.azurewebsites.net/health/db
```

둘 다 정상 응답이면 FastAPI 서버와 DB 연결이 모두 살아 있는 상태입니다.

## 자주 나는 문제

### Docker가 꺼져 있음

증상:

```text
failed to connect to the docker API
```

해결:

```text
Docker Desktop 실행 후 다시 시도
```

### Azure MySQL 연결 timeout

증상:

```text
Can't connect to MySQL server ... timed out
```

원인:

```text
Azure MySQL 방화벽에서 App Service 접근을 허용하지 않음
```

해결:

```text
Azure Portal > MySQL > Networking > Firewall rules 확인
```

### Azure MySQL secure transport 오류

증상:

```text
Connections using insecure transport are prohibited
```

해결:

```env
MYSQL_SSL_ENABLED=true
```

배포 환경에서는 이 값이 반드시 true여야 합니다.
