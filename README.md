# jamkkan-jeju-api

FastAPI, MySQL, Docker, Azure App Service 기반 백엔드 API 서버입니다.

## Frontend Usage

개발용 배포 서버:

```text
https://jankkan-jeju.azurewebsites.net
```

프론트엔드 프로젝트에서는 API base URL을 환경변수로 분리해서 사용합니다.

```env
NEXT_PUBLIC_API_BASE_URL=https://jankkan-jeju.azurewebsites.net
```

예시:

```ts
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

const response = await fetch(`${apiBaseUrl}/health`);
const data = await response.json();
```

서버 상태 확인:

- Health: https://jankkan-jeju.azurewebsites.net/health
- DB Health: https://jankkan-jeju.azurewebsites.net/health/db
- Swagger UI: https://jankkan-jeju.azurewebsites.net/docs

현재 개발용 서버 이름에 오타가 있습니다. `jankkan-jeju`는 개발용 서버 이름이며, 추후 운영 서버는 별도 이름으로 생성할 예정입니다.

## Local Backend

```powershell
Copy-Item .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

로컬 확인:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health
- DB Health: http://localhost:8000/health/db

로컬에서 외부 API까지 테스트하려면 `.env`에 실제 인증키를 넣어야 합니다. `.env`는 Git에 올리지 않습니다.

## Deployment

GitHub Actions CI/CD가 설정되어 있습니다.

Push 대상 브랜치:

- `dev`

배포 흐름:

```text
git push
-> GitHub Actions
-> Docker image build
-> Azure Container Registry push
-> Azure App Service deploy
```

배포 대상:

```text
ACR: jankkanjejuacr.azurecr.io/jamkkan-jeju-api
App Service: jankkan-jeju
```

`main` 브랜치는 추후 운영 서버 배포용으로 사용합니다.

자세한 내용은 [docs/architecture.md](docs/architecture.md), [docs/setup.md](docs/setup.md)를 참고합니다.
