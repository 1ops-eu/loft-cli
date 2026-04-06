# Compose Post-Deploy Example

Demonstrates v0.7 compose_project enhancements: plain file upload, HTTP readiness
check, post-deploy actions, and rebuild detection.

## What it does

1. Connects to the target server via SSH
2. Uploads `config/robots.txt` verbatim as `/opt/webapp/robots.txt` (**project.files**, #284)
3. Uploads and starts the httpd+redis compose stack
4. Waits for containers to be healthy
5. Polls `http://localhost:8080/` until HTTP 200 (**http_ready**, #283)
6. Runs three post-deploy actions after the stack is ready (**post_deploy**, #282)

## Rebuild detection (#287)

Set `rebuild: true` to always force-recreate containers on every apply (useful when
using `latest` image tags). When `rebuild: false` (default), containers are only
recreated if a pulled image digest changes.

## Usage

```bash
loft-cli validate examples/compose-post-deploy/compose-post-deploy.yaml
loft-cli plan    examples/compose-post-deploy/compose-post-deploy.yaml
loft-cli apply   examples/compose-post-deploy/compose-post-deploy.yaml
```

## Prerequisites

- A bootstrapped server with SSH access on port 2222
