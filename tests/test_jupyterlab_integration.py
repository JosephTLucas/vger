import pytest
import subprocess
import time
import os
import requests
from requests.exceptions import ConnectionError

# Adjust the path to V'ger's main module if necessary.
# Assuming tests/ is at the same level as vger/
VGER_CLI_PATH = ["python", "-m", "vger.application"]
JUPYTERLAB_HOST = "http://localhost:18888"
JUPYTERLAB_TOKEN = "vgeristesting"
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DOCKER_COMPOSE_FILE = os.path.join(TEST_DIR, "docker-compose.yml")

def is_jupyterlab_ready(url, token):
    try:
        response = requests.get(f"{url}/api/status", headers={"Authorization": f"token {token}"}, timeout=5)
        return response.status_code == 200
    except ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False

@pytest.fixture(scope="session", autouse=True)
def jupyterlab_service(request):
    print("\nStarting JupyterLab container for integration tests (pytest session)...")
    try:
        subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"], check=True, cwd=TEST_DIR)
        print("Waiting for JupyterLab to be ready...")
        ready = False
        for _ in range(45):  # Increased timeout slightly to 45s
            if is_jupyterlab_ready(JUPYTERLAB_HOST, JUPYTERLAB_TOKEN):
                ready = True
                break
            time.sleep(1)
        if not ready:
            # Try to capture logs if it fails to start
            print("JupyterLab did not become ready. Attempting to capture Docker logs...")
            try:
                logs = subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "logs"], capture_output=True, text=True, cwd=TEST_DIR)
                print(logs.stdout)
                print(logs.stderr)
            except Exception as log_e:
                print(f"Failed to capture Docker logs: {log_e}")
            # Then attempt to stop the container
            subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "down"], check=False, cwd=TEST_DIR)
            pytest.fail("JupyterLab container did not become ready in time.")
        print("JupyterLab is ready.")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start JupyterLab container: {e}")
    except Exception as e:
        pytest.fail(f"An error occurred during JupyterLab service setup: {e}")

    def fin():
        print("\nStopping JupyterLab container (pytest session)...")
        try:
            subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "down"], check=True, cwd=TEST_DIR)
            print("JupyterLab container stopped.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop JupyterLab container cleanly: {e}") # Log error but don't fail the teardown itself
        except Exception as e:
            print(f"An error occurred during JupyterLab service teardown: {e}")
            
    request.addfinalizer(fin)

# Test functions (no class needed unless for organization)

def test_01_lab_nb_list_empty():
    """Test listing notebooks on a fresh JupyterLab instance."""
    command = VGER_CLI_PATH + [
        "--platform", "jupyterlab",
        "--host", JUPYTERLAB_HOST,
        "--secret", JUPYTERLAB_TOKEN,
        "nb-list"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    
    assert result.returncode == 0, f"V'ger CLI command failed with error: {result.stderr}"
    assert "No running notebooks" in result.stdout, "Expected 'No running notebooks' for a fresh instance."

def test_02_lab_file_list_root():
    """Test listing files in the root directory of JupyterLab."""
    command = VGER_CLI_PATH + [
        "--platform", "jupyterlab",
        "--host", JUPYTERLAB_HOST,
        "--secret", JUPYTERLAB_TOKEN,
        "file-list", "--dir-path", "/"
    ]
    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0, f"V'ger CLI command failed with error: {result.stderr}"
    assert "\"type\": \"directory\"" in result.stdout, "Expected to see directory entries in root."
    assert "\"name\":" in result.stdout, "Expected to see file/dir names in root."
    assert "\"content\":" in result.stdout, "Expected 'content' key in JSON output for root dir."

def test_03_lab_run_terminal_echo():
    """Test running a simple echo command via the terminal."""
    test_string = "vger_echo_test_string_pytest"
    vger_command = VGER_CLI_PATH + [
        "--platform", "jupyterlab",
        "--host", JUPYTERLAB_HOST,
        "--secret", JUPYTERLAB_TOKEN,
        "terminal", "--code", f"echo {test_string}"
    ]
    result = subprocess.run(vger_command, capture_output=True, text=True)

    assert result.returncode == 0, f"V'ger CLI command failed with error: {result.stderr}"
    assert test_string in result.stdout.strip(), f"Expected '{test_string}' in terminal output. Got: {result.stdout.strip()}"

# To run with pytest, simply navigate to the root and run `pytest`
# If you want to run this file specifically: `pytest tests/test_jupyterlab_integration.py` 