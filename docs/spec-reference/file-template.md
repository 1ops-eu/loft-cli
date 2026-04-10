# kind: file_template

> Renders managed configuration files on the server from Jinja2 templates and variables. Change detection is hash-based — unchanged files are not re-written on re-apply.

Use `file_template` when you need to deploy configuration files with dynamic values: Nginx configs with server names, application `.env` files, cron configs, etc.

---

## What It Does

1. Renders the Jinja2 template with the provided variables
2. Computes a SHA-256 hash of the rendered content
3. Compares the hash against the recorded runtime state
4. If changed (or new), uploads the rendered file to the target path on the server
5. Optionally runs a `reload_command` after the file is written

---

## Example

```yaml
kind: file_template

meta:
  name: nginx-app-config
  description: Nginx reverse proxy config for the app

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

template:
  src: templates/nginx-app.conf.j2
  dest: /etc/nginx/sites-available/app
  owner: root
  group: root
  mode: "0644"
  reload_command: systemctl reload nginx
  vars:
    server_name: app.example.com
    upstream_port: 8080
    worker_processes: 4
```

With the template file at `templates/nginx-app.conf.j2`:

```jinja
server {
    listen 80;
    server_name {{ server_name }};

    location / {
        proxy_pass http://127.0.0.1:{{ upstream_port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Schema

### `template`

| Field | Type | Required | Description |
|---|---|---|---|
| `src` | string | Yes | Path to the Jinja2 template file, relative to the spec file |
| `dest` | string | Yes | Destination path on the server |
| `owner` | string | No | File owner on the server |
| `group` | string | No | File group on the server |
| `mode` | string | No | File permissions in octal string format (e.g. `"0644"`) |
| `reload_command` | string | No | Shell command to run on the server after the file is written |
| `vars` | dict | No | Variables to pass to the Jinja2 template |

---

## Template Rendering

Templates use standard [Jinja2](https://jinja.palletsprojects.com/) syntax. Variables defined in `vars` are available directly by name:

```jinja
{{ variable_name }}
{% if condition %}...{% endif %}
{% for item in items %}...{% endfor %}
```

Environment variables from `--env-file` are also available in the spec's `vars` values via `${VAR}` references:

```yaml
vars:
  db_password: ${DB_PASSWORD}
  server_name: ${SERVER_NAME}
```

---

## Idempotency

On re-apply, loft-cli computes the SHA-256 hash of the rendered template (with current variable values) and compares it to the recorded hash. If unchanged, the upload is skipped and the `reload_command` is not run.

This means changing a variable value (e.g. rotating a password) will cause the file to be re-rendered and re-uploaded on the next apply.
