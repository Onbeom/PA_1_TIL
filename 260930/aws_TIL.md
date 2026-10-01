# TIL — FastAPI MSA를 AWS EC2에 띄우기까지

## 프로젝트 구조: cluster-msa

군집(클러스터)과 그 안의 개별 노드를 별도 서비스로 분리한 3개의 FastAPI 마이크로서비스로 구성했다. gateway가 외부 요청의 단일 진입점이 되어 나머지 두 서비스로 라우팅하거나, 여러 서비스의 응답을 조합해 돌려준다.

- **gateway (8000)** — 외부 진입점. `/clusters/*`는 cluster-service로, `/nodes/*`는 node-service로 프록시하고, `/clusters/{id}/summary`에서는 두 서비스의 응답을 조합한다.
- **cluster-service (8001)** — 클러스터 자체의 메타데이터(이름, 리전, min/max/desired capacity)를 관리한다.
- **node-service (8002)** — 클러스터에 속한 개별 노드의 상태(등록, 시작, 정지, 종료)를 관리한다.

&#91;embedded content: gateway → cluster-service / node-service 프록시 구조\]

gateway가 클라이언트 요청을 받아 두 서비스로 나누어 프록시하고, summary 엔드포인트에서는 두 응답을 하나로 조합한다.

## EC2 인스턴스 생성과 SSH 접속

1. EC2 인스턴스 생성 시 키 페어를 지정하고 `.pem` 파일을 다운로드한다.
2. 키 파일 권한을 제한한다.

   ```bash
   chmod 400 my-key.pem
   ```
3. SSH로 접속한다.

   ```bash
   ssh -i my-key.pem ubuntu@<퍼블릭 IP>
   ```

## 배포: git clone → docker compose up

SSH로 EC2 안에 들어간 뒤, 미리 만들어둔 `cluster-msa` 프로젝트를 그대로 가져와서 띄웠다.

```bash
git clone <repo 주소>
cd cluster-msa
docker compose up --build
```

`gateway` · `cluster-service` · `node-service` 세 컨테이너가 모두 빌드되고, 헬스체크를 통과해 `Healthy` 상태로 올라온 것을 로그로 확인했다.

## 보안 그룹 포트 설정

| 포트 | 용도 | 이 프로젝트에서 |
| --- | --- | --- |
| 22 | SSH 접속 | 내 IP로 열어둠 |
| 80 | HTTP | 사용하지 않음 |
| 443 | HTTPS | 사용하지 않음 |
| 8000 | gateway API (Swagger UI) | 반드시 열어야 함 |

cluster-service(8001)·node-service(8002)는 내부 통신 전용이라 굳이 외부에 열지 않았다.

## 결과

`http://13.125.72.215:8000/docs` 접속에 성공했다. gateway의 Swagger UI가 그대로 뜨고, 여기서 `/clusters`, `/nodes` 엔드포인트를 직접 호출해볼 수 있다. 로컬에서 시작한 예제 MSA 백엔드가 실제 AWS EC2 위에서, 외부 브라우저로 접근 가능한 상태로 올라간 것을 확인한 시점이다.

## 배운 점과 다음 단계

- FastAPI에서 반환 타입 힌트는 `response_model`로 자동 추론되므로, 바디가 없는 상태코드(204 등)를 쓸 땐 타입 힌트를 빼거나 `response_model=None`을 명시해야 한다.
- Docker Desktop은 macOS·Windows용 GUI이고, Ubuntu는 `docker`/`docker compose` 명령이 커널의 Docker 엔진과 바로 통신하므로 따로 설치·실행할 필요가 없다.
- EC2는 키 페어 없이 만들면 로컬 SSH가 불가능하다 — 브라우저 기반 EC2 Instance Connect로 우회할 수 있지만, 로컬 터미널 접속을 원하면 키 페어를 지정해서 다시 만들어야 한다.
- 보안 그룹은 포트별로 따로 열어야 한다 — 80/443을 열었다고 8000이 자동으로 열리지 않는다.

### 다음 단계

- node-service 안에서 boto3로 실제 EC2 인스턴스 start/stop을 호출하도록 확장
- ECR에 이미지 푸시 → ECS(Fargate)로 세 서비스 배포
- 인메모리 저장소를 RDS(PostgreSQL)로 교체해 재시작해도 상태 유지
