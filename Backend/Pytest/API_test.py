import pytest
import sys, os

# adicionar a pasta Backend ao sys.path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # sobe de Pytest/ para Backend/
sys.path.insert(0, BASE_DIR)

from app import app
from io import BytesIO


# ============================================================================
# FIXTURE - Test Client
# ============================================================================

@pytest.fixture
def client():
    """
    Fixture que fornece um test client do Flask para usar em todos os testes.
    Ativa o modo TESTING para desabilitar tratamento de erros durante requisições.
    """
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================================
# TESTES - HOME E ERROR HANDLERS
# ============================================================================

def test_home_ok(client):
    """
    Testa GET / com sucesso.
    Valida: status 200 e mensagem esperada.
    """
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Flask backend is running 2.0!" in resp.data


def test_not_found_uses_error_handler(client):
    """
    Testa que rota inexistente dispara 404 com JSON padronizado.
    Valida: status 404 e estrutura de erro (code, name, description).
    """
    resp = client.get("/rota_inexistente")
    assert resp.status_code == 404
    data = resp.get_json()
    assert "error" in data
    assert data["error"]["code"] == 404
    assert data["error"]["name"] == "Not Found"
    assert "description" in data["error"]


def test_bad_request_missing_file_field(client):
    """
    Testa POST /files sem campo 'file'.
    Valida: status 400, formato de erro e mensagem específica.
    """
    resp = client.post("/files")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert data["error"]["code"] == 400
    assert data["error"]["name"] == "Bad Request"
    assert "You must upload a file" in data["error"]["description"]


# ============================================================================
# TESTES - GESTÃO DE FICHEIROS (/files) – só contrato HTTP
# ============================================================================

def test_add_file_shp_direct_returns_400(client):
    """
    Testa upload de ficheiro .shp sem ZIP.
    Valida: status 400 e mensagem de erro específica.
    """
    fake_content = b"dummy shp content"
    data = {"file": (BytesIO(fake_content), "layer.shp")}

    resp = client.post("/files", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == 400
    assert "Please upload shapefiles as a .zip" in body["error"]["description"]


def test_add_geojson_contract(client):
    """
    Testa contrato de POST /files com .geojson.
    Não valida I/O, só que a chamada responde com JSON.
    """
    fake_content = b'{"type": "FeatureCollection", "features": []}'
    data = {"file": (BytesIO(fake_content), "layer.geojson")}

    resp = client.post("/files", data=data, content_type="multipart/form-data")
    assert resp.status_code in (200, 400)  # depende da lógica interna
    body = resp.get_json()
    assert isinstance(body, dict)


# ============================================================================
# TESTES - GESTÃO DE SCRIPTS (/scripts)
# ============================================================================

def test_add_script_ok(client):
    resp = client.post("/scripts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "message" in data
    assert "script_id" in data
    assert "Script added successfully" in data["message"]


def test_list_scripts_ok(client):
    resp = client.get("/scripts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "scripts" in data
    assert isinstance(data["scripts"], list)
    assert "message" in data


def test_script_metadata_ok(client):
    resp = client.get("/scripts/script123")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["script_id"] == "script123"
    assert "output" in data


def test_remove_script_ok(client):
    resp = client.delete("/scripts/script123")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "message" in data
    assert "script123" in data["message"]


# ============================================================================
# TESTES - EXECUÇÃO DE SCRIPTS (/execute_script)
# ============================================================================

def test_execute_script_post_ok(client):
    payload = {"parameters": {"input": "value1", "mode": "test"}}
    resp = client.post("/execute_script/script123", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Running script" in data["message"]
    assert data["parameters"] == payload["parameters"]


def test_execute_script_without_parameters(client):
    resp = client.post("/execute_script/script123", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "parameters" in data


def test_stop_script_ok(client):
    resp = client.delete("/execute_script/script123", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "stopped" in data["message"]

def test_get_script_status_ok(client):
    resp = client.get("/execute_script/script123")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["script_id"] == "script123"
    assert "status" in data


def test_get_script_output_ok(client):
    resp = client.get("/execute_script/script123/output")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["script_id"] == "script123"
    assert "output" in data


# ============================================================================
# TESTES - LAYERS (/layers)
# ============================================================================

def test_add_layer_ok(client):
    fake_content = b"dummy layer content"
    data = {
        "layer_file": (BytesIO(fake_content), "layer.tif"),
        "layer_name": "Meu Layer"
    }

    resp = client.post("/layers", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "layer_id" in body
    assert "message" in body
    assert "Meu Layer" in body["message"]


def test_add_layer_without_name(client):
    fake_content = b"dummy layer content"
    data = {"layer_file": (BytesIO(fake_content), "default_layer.tif")}

    resp = client.post("/layers", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "layer_id" in body


def test_export_layer_ok(client):
    resp = client.put("/layers/layer123", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "exported" in data["message"]


def test_remove_layer_ok(client):
    resp = client.delete("/layers/layer123", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "removed" in data["message"]


def test_set_layer_priority_ok(client):
    resp = client.post("/layers/layer123/5", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "priority" in data["message"].lower()
    assert data["New priority"] == "5"


def test_layer_information_ok(client):
    resp = client.get("/layers/layer123/information")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["layer_id"] == "layer123"
    assert "info" in data
    assert "geometry" in data["info"]
    assert "features" in data["info"]


def test_extract_layer_table_data_ok(client):
    resp = client.get("/layers/layer123/table")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["layer_id"] == "layer123"
    assert "table_data" in data
    assert isinstance(data["table_data"], list)
    if len(data["table_data"]) > 0:
        assert "name" in data["table_data"][0]
        assert "type" in data["table_data"][0]
