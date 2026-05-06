# SwiftDeploy

A declarative CLI tool that generates and manages a containerised service stack from a single manifest.yaml.

## Setup

```bash
# Build the image
docker build -t swift-deploy-1-node:latest .

# Install dependency
pip3 install pyyaml

# Run commands
./swiftdeploy init
./swiftdeploy validate
./swiftdeploy deploy
./swiftdeploy promote canary
./swiftdeploy promote stable
./swiftdeploy teardown --clean
```

## Subcommands

| Command | Description |
|---|---|
| `init` | Generate nginx.conf and docker-compose.yml from manifest |
| `validate` | Run 5 pre-flight checks |
| `deploy` | Init + bring up stack + wait for health |
| `promote canary` | Switch to canary mode with rolling restart |
| `promote stable` | Switch back to stable mode |
| `teardown` | Stop all containers |
| `teardown --clean` | Stop all + delete generated configs |

## Endpoints

- `GET /` — welcome message with mode, version, timestamp
- `GET /healthz` — liveness check with uptime
- `POST /chaos` — simulate degraded behaviour (canary only)

## Blog Post
https://https://my-tech-journeyy.hashnode.dev/how-i-built-swiftdeploy-a-self-configuring-deployment-tool-with-opa-policy-enforcement-and-real-time-observability
