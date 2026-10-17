# tatou
A web platform for pdf watermarking. This project is intended for pedagogical use, and contain security vulnerabilities. Do not deploy on an open network.

## Instructions

The following instructions are meant for a bash terminal on a Linux machine. If you are using something else, you will need to adapt them.

To clone the repo, you can simply run:

```bash
git clone https://github.com/nharrand/tatou-2026.git
```

Note that you should probably fork the repo and clone your own repo.


### Run python unit tests

```bash
cd tatou/server

# Create a python virtual environement
python3 -m venv .venv

# Activate your virtual environement
. .venv/bin/activate

# Install the necessary dependencies
python -m pip install -e ".[dev]"

# Run the unit tests
python -m pytest
```

### Deploy

From the root of the directory:

```bash
# Create a file to set environement variables like passwords.
cp sample.env .env

# Edit .env and pick the passwords you want

# Rebuild the docker image and deploy the containers
docker compose up --build -d

# Monitor logs in realtime 
docker compose logs -f

# Test if the API is up
http -v :5000/healthz

# Open your browser at 127.0.0.1:5000 to check if the website is up.
```



### Run RMAP security tests

The RMAP security tests are included in the Docker image.

Before testing, make sure the server's private key is in place and the passphrase is set:

1. Copy the server private key to `server/keys/server_priv.asc`. Never commit this file; it is listed in `.gitignore`.
2. Set `RMAP_SERVER_PASSPHRASE` in `.env` (copied from `sample.env`).
3. Load the variables into your shell:

```bash
set -a
source .env
set +a
```

From the root of the repository, run:

```bash
docker compose exec server python -m pytest test/rmap/
```

The tests cover:

* successful RMAP handshake
* replay of a previously used Message 2
* rejection of an unmatched server nonce
* rejection of an unregistered identity

A successful run should show:

```text
4 passed
```
### Mutation testing (Specialization B)

Mutation testing checks whether the test suite notices small faults injected into the code. We use [mutmut](https://github.com/boxed/mutmut) to mutate the watermarking methods in `server/src/`, and run only the tests in `server/test/mutation/` against each mutant.

mutmut reads its settings from `server/pyproject.toml`:

```toml
[tool.mutmut]
source_paths = [
    "src/add_after_eof.py",
    "src/hidden_comment_watermark.py",
    "src/metadata_watermark.py",
    "src/invisible_text_watermark.py",
]
also_copy = [
	"src/watermarking_utils.py",
	"src/watermarking_method.py",
	"src/unsafe_bash_bridge_append_eof.py",
]
pytest_add_cli_args_test_selection = ["test/mutation/"]
on_dependency_change = "rerun"
```

Run it inside the server container, or in the same virtual environment used for the unit tests:

```bash
cd tatou/server

# Install mutmut in the active environment
python -m pip install mutmut

# Confirm the mutation tests pass on the unmodified code first
python -m pytest test/mutation/

# Generate and run mutants against the watermarking methods
python -m mutmut run

# List the mutants that survived the tests
python -m mutmut results

# Show one surviving mutant as a diff
python -m mutmut show <mutant-id>
```

A surviving mutant means no test failed when that line changed. Read each one and decide whether the tests need a stronger assertion, an edge case, or whether the mutant is equivalent to the original code.


### Fuzzing campaign (Specialization A)

The fuzzing campaign targets the `GET /api/get-version/<link>` endpoint. It tests boundary-length inputs, unusual characters, SQL-related strings, encoded path traversal attempts, Unicode, random strings, and invalid links. A valid-link positive control is also used to check expected endpoint behaviour.

**Run the fuzzing campaign**

From the repository root, with the Tatou API and database running:

```bash
python fuzz_get_version.py
```

**Run regression tests**

```bash
python -m pytest server/test/test_get_version_regression.py -v
```

**Results and evidence**

- `fuzz_get_version_results.csv` — fuzzing results.
- `fuzz_results_run1.csv` — results from the initial run.
- `artifacts/hansika/fuzzing/fuzzing_campaign.log` — campaign log.
- `server/test/test_get_version_regression.py` — non-regression tests.

The accompanying fuzzing report documents the findings, remediation status, and test results. The campaign should only be run against an authorised test instance.

### Operational Security (Specialization D)

The operational security work focused on threat modelling, failed-login monitoring, reducing database port exposure, and incident response following the FLAG_2 incident.

*Security improvements*

- Failed login attempts are recorded in application logs, with a warning generated after three failed attempts for the same email address within five minutes.
- The database port published through Docker Compose was removed to reduce direct database exposure through a host-published port.
- A command-injection weakness in the bash-bridge-eof watermarking method was addressed by replacing the shell-based approach with direct Python PDF processing.
- The FLAG_2 incident was documented, the flag was rotated, and the server was redeployed.

Artifacts and evidence:
- `docs/operational-security/THREAT_MODEL.md` — threat model.
- `docs/operational-security/INCIDENT_RECORD.md` — incident investigation and remediation.
- `evidence/failed-login-evidence.txt` and `evidence/repeated-login-evidence.txt` — login-monitoring evidence.
- `server/src/server.py` and `docker-compose.yml` — implementation changes.

The login-monitoring tests confirmed that failed attempts were logged and repeated failures generated warnings under the tested conditions. Monitoring does not automatically block accounts or IP addresses.

