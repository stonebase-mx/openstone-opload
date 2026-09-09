<!--
  This file is kept byte-identical to `opload/README.md` (the PyPI long description read by
  `opload/setup.py`). Edit both copies together; the unit test
  `opload/src/test/test_opload/test_readme.py` fails when they differ.
-->
# opload

**Opload: Open Loading Server** — a minimal key-value "loading" REST server built on
[fred-oss](https://github.com/stonebase-mx/fahera-fred-oss). It exposes four HTTP endpoints
(`/`, `/get`, `/set`, `/keys`) over a value store whose backend is pluggable: an in-memory store
by default, or Redis / MinIO through fred-oss's service catalog. Everything the server does — the
FastAPI/uvicorn server, the router annotations, the `keyval` component and the backends — comes
from the pinned `fred-oss` release; `opload` itself is a thin router catalog plus a CLI.

> **Maturity: ALPHA.** `opload` declares itself at the ALPHA maturity level and logs a warning
> saying so on every import ("The opload implementation is in early development and therefore
> currently with incomplete and unstable features"). Expect incomplete and unstable features.
> Set `FRD_DISABLE_MATURITY_WARN=1` to silence the warning.

## Install

Requires **Python 3.12 or newer** (`python_requires >= 3.12`). The only runtime dependency is
`fred-oss`, pinned in `opload/requirements.txt` (currently `fred-oss==0.60.0`).

From PyPI:

```bash
pip install opload
```

Editable install from a clone (for development):

```bash
git clone https://github.com/stonebase-mx/openstone-opload.git
cd openstone-opload
pip install -e opload
```

Both forms install the `opload` console script (`opload=opload.cli:CLI.cli_exec`).

## Quick start

Start the server with the default in-memory (`STDLIB`) backend. For local play, disable the API
key check:

```bash
FRD_RESTAPI_DISABLE_AUTH=1 opload serve
```

The server listens on `http://0.0.0.0:8000` by default. Then, from another shell:

```bash
# health check
curl -s http://localhost:8000/
# {"ok":true,"host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*"}

# a key that does not exist yet -> "val": null
curl -s "http://localhost:8000/get?key=demo/1.txt"
# {"ok":true,"key":"demo/1.txt","val":null,"host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*"}

# store a value (JSON body)
curl -s -X POST http://localhost:8000/set \
  -H "Content-Type: application/json" \
  -d '{"key": "demo/1.txt", "value": "Hello, world."}'
# {"ok":true,"key":"demo/1.txt","val":"Hello, world.","host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*","content-type":"application/json","content-length":"47"}

# read it back
curl -s "http://localhost:8000/get?key=demo/1.txt"
# {"ok":true,"key":"demo/1.txt","val":"Hello, world.","host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*"}

# read only the raw value, without the envelope
curl -s "http://localhost:8000/get?key=demo/1.txt&direct_val=1"
# "Hello, world."

# list keys (glob pattern, default "*")
curl -s "http://localhost:8000/keys"
# {"ok":true,"pattern":"*","keys":["demo/1.txt"],"host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*"}
curl -s "http://localhost:8000/keys?pattern=demo/*"
# {"ok":true,"pattern":"demo/*","keys":["demo/1.txt"],"host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*"}
```

The `host`, `user-agent`, `accept`, … fields are the request headers echoed back — see
[API reference](#api-reference) for why.

### Authenticated form

Without `FRD_RESTAPI_DISABLE_AUTH`, every endpoint requires an API key. The key is the value of
`FRD_RESTAPI_TOKEN` and is presented in the **`X-API-Key` request header** (an `APIKeyHeader`
security scheme; there is no `Authorization: Bearer` form). A missing or wrong key gets
`401 {"detail":"Invalid or missing API Key"}`.

```bash
FRD_RESTAPI_TOKEN=s3cret opload serve
```

```bash
curl -s http://localhost:8000/
# {"detail":"Invalid or missing API Key"}

curl -s http://localhost:8000/ -H "X-API-Key: s3cret"
# {"ok":true,"host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*","x-api-key":"s3cret"}

curl -s -X POST http://localhost:8000/set \
  -H "X-API-Key: s3cret" -H "Content-Type: application/json" \
  -d '{"key": "demo/1.txt", "value": "Hello, world."}'
# {"ok":true,"key":"demo/1.txt","val":"Hello, world.","host":"localhost:8000","user-agent":"curl/7.88.1","accept":"*/*","x-api-key":"s3cret","content-type":"application/json","content-length":"47"}
```

**Always set `FRD_RESTAPI_TOKEN` on a real deployment.** When it is unset the server logs
`FRD_RESTAPI_TOKEN not found in environment; using default token 'changeme'.` and accepts
`X-API-Key: changeme`.

FastAPI's interactive docs are served at `/docs` (and the schema at `/openapi.json`).

## Configuration

Everything is configured through environment variables. `OPLOAD_*` is read by `opload`
itself; `FRD_RESTAPI_*` and the rest are read by fred-oss.

| Variable | Default | Meaning |
|---|---|---|
| `OPLOAD_BACKEND_SERVICE` | `STDLIB` | Backend service for the key-value store, passed as `service_name` to the `MAIN` router. One of the fred-oss `ServiceCatalog` names: `STDLIB`, `REDIS`, `MINIO` (case-insensitive). Any other value makes `opload serve` exit with `KeyError`. |
| `FRD_RESTAPI_HOST` | `0.0.0.0` | Bind address for uvicorn. |
| `FRD_RESTAPI_PORT` | `8000` | Bind port for uvicorn. |
| `FRD_RESTAPI_LOGLEVEL` | `info` | uvicorn log level (lower-cased). |
| `FRD_RESTAPI_DISABLE_AUTH` | `false` | `1` / `true` / `yes` / `on` disables the `X-API-Key` check on every endpoint. |
| `FRD_RESTAPI_TOKEN` | `changeme` (with a warning) | The API key expected in the `X-API-Key` header. **Set it**: the default is public knowledge. |
| `FRD_RESTAPI_INCLUDE_ROUTERS` | _(empty = all)_ | `;`-separated router names to register (`BASE`, `MAIN`); everything else is skipped. |
| `FRD_RESTAPI_EXCLUDE_ROUTERS` | _(empty = none)_ | `;`-separated router names to skip. `FRD_RESTAPI_EXCLUDE_ROUTERS=BASE` drops `/`, `=MAIN` drops `/get`, `/set`, `/keys`. |
| `FRD_RESTAPI_EXCLUDE_BUILTIN_ROUTERS` | `false` | Defined in fred-oss `rest/settings.py` but **not consumed anywhere** in fred-oss 0.60.0; setting it has no effect. |
| `FRD_RESTAPI_ROUTERCATALOG_CLASSNAME` | `RouterCatalog` | Router catalog class used by a bare `fred serve`. `opload serve` always passes `RouterCatalog` explicitly. |
| `FRD_RESTAPI_ROUTERCATALOG_CLASSPATH` | `fred.rest.router.catalog.default` | Module holding that class. Set it to `opload.router.catalog` to make a bare `fred serve` serve opload (see [CLI](#cli)). |
| `FRD_DISABLE_MATURITY_WARN` | `0` | `1` / `true` / `yes` silences the ALPHA maturity warnings logged at import time. |

CORS is hard-wired to `allow_origins=["*"]` (all methods, all headers, credentials allowed) in
fred-oss 0.60.0 and is not configurable.

### Backends

The backend list is exactly the fred-oss `ServiceCatalog` enum (`STDLIB`, `REDIS`, `MINIO`).
The service client is created lazily, so `opload serve` starts (and `/` answers) even when the
configured Redis/MinIO is unreachable; the first `/get`, `/set` or `/keys` then fails with
`500 Internal Server Error`.

**`STDLIB`** (default) — an in-memory Python `dict` inside the server process. Process-local:
not shared between workers or replicas, and everything is lost on restart. Needs no configuration.
`/keys` filters with `fnmatch` (shell-style glob). `presigned_url` is ignored (a warning is
logged and the plain value is returned).

**`REDIS`** — a Redis key space (`GET` / `SET` / `DEL`; `/keys` uses `SCAN MATCH <pattern>`).
Connection settings, all optional:

| Variable | Default |
|---|---|
| `REDIS_HOST` | `localhost` |
| `REDIS_PORT` | `6379` |
| `REDIS_PASSWORD` | _(none)_ |
| `REDIS_DB` | `0` |

`presigned_url` is ignored for Redis.

**`MINIO`** — an S3-compatible object store. Each key is stored as an object whose content is
the value (`/set` uploads `value` as UTF-8 bytes; `/get` downloads it and returns it decoded as
UTF-8, or base64 if the bytes are not valid UTF-8). Connection settings:

| Variable | Default |
|---|---|
| `MINIO_ENDPOINT` | `localhost:9000` |
| `MINIO_ACCESS_KEY` | `minioadmin` |
| `MINIO_SECRET_KEY` | `minioadmin` |
| `MINIO_REGION` | `us-east-1` |
| `MINIO_SECURE` | effectively always `true` (any value, including `false`, is truthy in 0.60.0) — connections are made over HTTPS |
| `MINIO_BUCKET` | _(none)_ — see below |

The bucket comes either from `MINIO_BUCKET` or from the key itself: the object path is
`MINIO_BUCKET/<key>`, its directory part is the bucket and its basename the object name. So with
`MINIO_BUCKET` unset, `key=mybucket/demo/1.txt` targets bucket `mybucket/demo`… and a key
without a `/` fails with "Bucket name must be specified". `/set` creates the bucket if it does not
exist. `/keys` needs `MINIO_BUCKET` and lists the objects of that bucket, filtered by
`fnmatch` against `pattern`.

`presigned_url=1` on `/get` returns, instead of the object content, a **presigned GET URL** for
the object (valid for 6 hours) so a client can download it straight from the object store. This
is what the flag means for object-store backends; the other backends ignore it.

Note: in fred-oss 0.60.0 the backend factory logs `[ERROR] Unknown service 'MINIO'... will attempt
to use provided kwargs as-is.` at startup and then initialises MinIO normally from the variables
above. The message is spurious.

## CLI

The `opload` console script is a [python-fire](https://github.com/google/python-fire) CLI, so
flags are `--name value` and the built-in help is reached with `opload -- --help` (a plain
`opload serve --help` crashes with `unexpected keyword argument 'help'` because `serve` forwards
unknown flags).

```bash
opload version
# 0.4.0
```

Prints the contents of the `opload/src/main/opload/version` file.

```bash
opload serve [--classname RouterCatalog] [--classpath opload.router.catalog] [<fred serve flags>]
```

Starts the server. `--classname` and `--classpath` default to opload's own router catalog; any
other flag is forwarded to `fred serve`, which accepts:

| Flag | Value | Meaning |
|---|---|---|
| `--include_routers` | list, e.g. `'["MAIN"]'` | Register only these routers (`BASE`, `MAIN`). |
| `--exclude_routers` | list, e.g. `'["BASE"]'` | Skip these routers. |
| `--fastapi_configs` | dict, e.g. `'{"title": "Opload"}'` | Keyword arguments for the `FastAPI(...)` app constructor. |
| `--server_configs` | dict, e.g. `'{"host": "127.0.0.1", "port": 9001}'` | Keyword arguments for `uvicorn.run(...)`; `host` / `port` here override `FRD_RESTAPI_HOST` / `FRD_RESTAPI_PORT`. |

Examples:

```bash
opload serve --server_configs '{"host": "127.0.0.1", "port": 9001}'
opload serve --exclude_routers '["MAIN"]'   # only "/" is served
```

`opload serve` is equivalent to running fred-oss's own CLI against opload's catalog:

```bash
fred serve --classname RouterCatalog --classpath opload.router.catalog
```

or, with the env-var route, a bare `fred serve`:

```bash
FRD_RESTAPI_ROUTERCATALOG_CLASSNAME=RouterCatalog \
FRD_RESTAPI_ROUTERCATALOG_CLASSPATH=opload.router.catalog \
fred serve
```

(A bare `fred serve` with neither serves fred-oss's default example catalog, not opload.)

## API reference

All responses are JSON. Two behaviours apply to every endpoint:

- **Everything unknown is echoed back.** The router merges the request headers, path params,
  query params and (for `POST`) the JSON body into one keyword dict and passes it to the handler;
  whatever the handler does not declare comes back in the response envelope (`**kwargs`). That
  is why `host`, `user-agent`, `accept` — and `x-api-key` when auth is on — appear in the
  responses above, and why `/get?key=k&extra=1` answers with `"extra":"1"`.
- **Boolean flags are strings.** Query values arrive as strings and are tested for truthiness,
  so any non-empty value enables a flag — `direct_val=false` still enables `direct_val`. To
  disable a flag, omit it.

| Method | Path | Params | Answer |
|---|---|---|---|
| `GET` | `/` | `include_telemetry` (flag, default off) | `{"ok": true}`; with the flag, adds `"telemetry": {"snapshot_at", "cpu_percent", "virtual_memory_percent", "swap_memory_percent", "disk_usage_percent"}` (a runtime profiling snapshot; `cpu_percent` samples for 1 s). |
| `GET` | `/get` | `key` (str, required) · `presigned_url` (flag) · `direct_val` (flag) | `{"ok": true, "key": key, "val": val}`; `val` is `null` for a missing key. `direct_val` returns the raw value alone (a JSON string, or `null`) instead of the envelope. `presigned_url` asks the backend for a presigned download URL instead of the content (MinIO only; ignored elsewhere). |
| `POST` | `/set` | JSON body `{"key": str, "value": str}` | `{"ok": true, "key": key, "val": value}`. Extra body fields are forwarded to the backend's `set` (Redis honours an integer `expire` in seconds; the others log "Additional kwargs ignored"). |
| `GET` | `/keys` | `pattern` (str, default `"*"`) | `{"ok": true, "pattern": pattern, "keys": [...]}` — glob (`fnmatch`) on `STDLIB` / `MINIO`, `SCAN MATCH` on `REDIS`. |

Missing required params (e.g. `/get` without `key`) produce a `500` from the handler's
`TypeError`, not a `422`.

## Development

Layout:

```
opload/                        # the Python package (setup.py, requirements.txt, MANIFEST.in, README.md)
  src/main/opload/             # package sources
    __init__.py                # ALPHA maturity declaration
    cli.py                     # `opload` console script (version, serve)
    settings.py                # OPLOAD_BACKEND_SERVICE
    version                    # the version string (read by setup.py and `opload version`)
    router/catalog.py          # RouterCatalog: BASE -> RouterBaseMixin, MAIN -> RouterMainMixin
    router/_base.py            # GET /
    router/_main.py            # GET /get, POST /set, GET /keys
  src/test/                    # pytest suite
check-style.sh  check-types.sh  tests-unit.sh  tests-coverage.sh
requirements-develop.txt
```

`setup.py` resolves the source root from `CODEBASE_PATH` (default `src/main`) and reads the
version from `src/main/opload/version` and the long description from `opload/README.md`.

Set up a dev environment:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-develop.txt
pip install -e opload
```

Scripts (run from the repository root):

| Script | Runs |
|---|---|
| `bash check-style.sh` | `pycodestyle opload --max-line-length 120` |
| `bash check-types.sh` | `mypy opload --ignore-missing-imports --install-types --non-interactive` |
| `bash tests-unit.sh` | `coverage run -m pytest src/test` inside `opload/` |
| `bash tests-coverage.sh` | `coverage report --omit="test_*"` inside `opload/` (after `tests-unit.sh`) |

Run a single test:

```bash
(cd opload; python -m pytest src/test/test_opload/test_version.py -k test_get_current_version)
```

The suite includes `test_readme.py`, which asserts that `README.md` and `opload/README.md` are
byte-identical — edit both when you change one.

## Release

1. Bump `opload/src/main/opload/version` in your PR (recent history: "OLD-6 Update minor
   version"). Nothing else carries the version.
2. Open the PR against `main`. Two workflows run on every pull request:
   - `check-tests.yaml` — installs `requirements-develop.txt` and the package, then runs
     `tests-unit.sh` and `tests-coverage.sh` on Python 3.12;
   - `check-wheel.yaml` — builds a wheel (`python setup.py bdist_wheel`), installs it and runs
     `opload version`.
3. Merging into `main` a PR that touched `opload/**` (or the publish workflow itself) triggers
   `package-publish.yaml`: it builds an sdist and uploads it to PyPI with
   `twine upload --skip-existing` using the `PYPI Package Publishing` environment. An unchanged
   version is skipped, so a PR that only edits `opload/README.md` without a bump does not refresh
   the PyPI page until the next version bump.

## License

MIT — see [`LICENSE`](LICENSE). Copyright (c) 2025 Open Stone Software (OSS).
