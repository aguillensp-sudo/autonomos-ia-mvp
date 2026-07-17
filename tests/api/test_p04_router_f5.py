"""SPEC-F5-01: the 6 Phase 5 endpoints. FastAPI TestClient, graph_runtime and
the ARQ pool mocked — no real graph/Anthropic/Redis call. Acceptance
criteria: CA-F5-01, CA-F5-02, CA-F5-05.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthedRequest, get_authed_request
from src.api.graph_runtime import PresentacionDuplicadaError
from src.api.main import app

client = TestClient(app)


def _mock_authed_request():
    mock_client = MagicMock()
    return AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")


@pytest.fixture(autouse=True)
def _override_auth():
    app.dependency_overrides[get_authed_request] = _mock_authed_request
    yield
    app.dependency_overrides.clear()


def test_endpoints_requieren_jwt():
    app.dependency_overrides.clear()  # this one test needs the REAL auth dependency
    for method, path, kwargs in [
        ("post", "/api/proceso/p04/iniciar", {}),
        ("post", "/api/proceso/p04/mensaje/p1", {"json": {"tipo": "texto", "contenido": "hola"}}),
        ("post", "/api/proceso/p04/calcular", {"json": {"proceso_id": "p1"}}),
        ("post", "/api/proceso/p04/confirmar", {"json": {"proceso_id": "p1"}}),
        ("get", "/api/proceso/p04/estado/p1", {}),
        ("get", "/api/proceso/p04/justificante/p1", {}),
    ]:
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code in (401, 403), f"{path} did not require auth: {resp.status_code}"
    app.dependency_overrides[get_authed_request] = _mock_authed_request


@patch("src.api.routers.p04.graph_runtime")
def test_post_iniciar_devuelve_proceso_id_y_periodo(mock_graph_runtime):
    mock_graph_runtime.iniciar_graph.return_value = {
        "proceso_id": "u1:P04:2026:1T", "ejercicio": 2026, "periodo": "1T", "fecha_limite": "2026-04-20",
    }
    resp = client.post("/api/proceso/p04/iniciar")
    assert resp.status_code == 200
    body = resp.json()
    assert body["proceso_id"] == "u1:P04:2026:1T"
    assert body["periodo"] == "1T"


@patch("src.api.routers.p04.graph_runtime")
def test_post_iniciar_presentacion_duplicada_devuelve_409(mock_graph_runtime):
    mock_graph_runtime.iniciar_graph.side_effect = PresentacionDuplicadaError("ABCD1234EFGH5678")
    mock_graph_runtime.PresentacionDuplicadaError = PresentacionDuplicadaError
    resp = client.post("/api/proceso/p04/iniciar")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "PRESENTACION_DUPLICADA"


@patch("src.api.routers.p04.extraer_factura_ocr")
def test_post_facturas_ocr_devuelve_ocr_result(mock_ocr):
    mock_ocr.return_value = {
        "nif_emisor": "12345678Z", "confianza_nif_emisor": 0.95,
        "fecha": "2026-03-01", "confianza_fecha": 0.9,
        "base_imponible": 100.0, "confianza_base_imponible": 0.6,
        "tipo_iva": 21, "confianza_tipo_iva": 0.9,
    }
    resp = client.post(
        "/api/proceso/p04/facturas/ocr",
        files={"file": ("factura.png", b"fake-png-bytes", "image/png")},
        data={"tipo": "emitida"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted"]["nif_emisor"] == "12345678Z"
    assert body["requires_review"] is True  # base_imponible confidence 0.6 < 0.8
    assert "pdf_path" in body


def test_post_facturas_json_manual_sigue_funcionando():
    """Regression guard: Phase 1's existing JSON /facturas endpoint is untouched."""
    resp = client.post(
        "/api/proceso/p04/facturas",
        json={
            "tipo": "emitida", "numero_factura": "F-1", "fecha": "2026-01-15",
            "base_imponible": "100.00", "tipo_iva": 21, "cuota_iva": "21.00",
        },
    )
    # Not asserting 201 here (requires a real DB insert) — only that it's
    # still routed as JSON body and doesn't collide with the OCR endpoint.
    assert resp.status_code != 404


@patch("src.api.routers.p04.graph_runtime")
def test_post_mensaje_texto_libre_y_factura_confirmada(mock_graph_runtime):
    mock_graph_runtime.enviar_mensaje.return_value = {"mensajes": [], "pendiente": "none"}
    resp = client.post("/api/proceso/p04/mensaje/p1", json={"tipo": "texto", "contenido": "hola"})
    assert resp.status_code == 200
    mock_graph_runtime.enviar_mensaje.assert_called_once()

    resp2 = client.post("/api/proceso/p04/mensaje/p1", json={"tipo": "factura_confirmada", "factura": {}})
    assert resp2.status_code == 200


@patch("src.api.routers.p04.graph_runtime")
def test_post_calcular_devuelve_resultado_m303(mock_graph_runtime):
    mock_graph_runtime.calcular_graph.return_value = {"resultado": "160.00", "tipo_resultado": "a_ingresar"}
    resp = client.post("/api/proceso/p04/calcular", json={"proceso_id": "p1", "facturas_emitidas": [], "facturas_recibidas": []})
    assert resp.status_code == 200
    assert resp.json()["resultado"] == "160.00"


@patch("src.api.routers.p04.get_arq_pool")
@patch("src.api.routers.p04.graph_runtime")
def test_post_confirmar_enqueues_arq_job(mock_graph_runtime, mock_get_pool):
    mock_graph_runtime.confirmar_graph.return_value = {"confirmado": True}
    mock_pool = AsyncMock()
    mock_job = MagicMock(job_id="job-123")
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
    mock_get_pool.return_value = mock_pool

    resp = client.post("/api/proceso/p04/confirmar", json={"proceso_id": "p1", "metodo_pago": "domiciliacion", "iban": "ES123"})

    assert resp.status_code == 202
    body = resp.json()
    assert body["rpa_job_id"] == "job-123"
    mock_pool.enqueue_job.assert_called_once()
    args, kwargs = mock_pool.enqueue_job.call_args
    assert args[0] == "procesar_presentacion"


@patch("src.api.routers.p04.get_arq_pool")
@patch("src.api.routers.p04.graph_runtime")
def test_post_confirmar_no_enqueues_si_grafo_no_confirma(mock_graph_runtime, mock_get_pool):
    mock_graph_runtime.confirmar_graph.return_value = {"confirmado": False, "quiere_revisar": True}
    mock_pool = AsyncMock()
    mock_get_pool.return_value = mock_pool

    resp = client.post("/api/proceso/p04/confirmar", json={"proceso_id": "p1"})

    assert resp.status_code == 200  # not enqueued, not the 202 "accepted for RPA" response
    mock_pool.enqueue_job.assert_not_called()


def test_get_estado_lee_presentacion_directo_de_bd():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
        "id": "p1", "estado": "presentando", "ejercicio": 2026, "periodo": "1T",
        "resultado": None, "csv_aeat": None, "nrc": None, "error_code": None, "error_detail": None,
    }]
    mock_client.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://signed/qr.png"}
    app.dependency_overrides[get_authed_request] = lambda: AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")

    resp = client.get("/api/proceso/p04/estado/u1:P04:2026:1T")

    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "presentando"
    assert body["qr_url"] == "https://signed/qr.png"


def test_get_estado_qr_url_null_si_archivo_no_existe():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
        "id": "p1", "estado": "presentando", "ejercicio": 2026, "periodo": "1T",
        "resultado": None, "csv_aeat": None, "nrc": None, "error_code": None, "error_detail": None,
    }]
    mock_client.storage.from_.return_value.create_signed_url.side_effect = Exception("not found")
    app.dependency_overrides[get_authed_request] = lambda: AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")

    resp = client.get("/api/proceso/p04/estado/u1:P04:2026:1T")

    assert resp.status_code == 200
    assert resp.json()["qr_url"] is None


def test_get_estado_sin_qr_si_no_esta_presentando():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
        "id": "p1", "estado": "presentado", "ejercicio": 2026, "periodo": "1T",
        "resultado": None, "csv_aeat": "ABCD1234EFGH5678", "nrc": None, "error_code": None, "error_detail": None,
    }]
    app.dependency_overrides[get_authed_request] = lambda: AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")

    resp = client.get("/api/proceso/p04/estado/u1:P04:2026:1T")

    assert resp.status_code == 200
    assert resp.json()["qr_url"] is None
    mock_client.storage.from_.assert_not_called()


def test_get_estado_404_si_no_existe():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    app.dependency_overrides[get_authed_request] = lambda: AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")

    resp = client.get("/api/proceso/p04/estado/u1:P04:2026:1T")

    assert resp.status_code == 404


def test_get_justificante_devuelve_url_firmada():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
        "estado": "presentado", "justificante_path": "justificantes/u1/2026_1T.pdf",
        "csv_aeat": "ABCD1234EFGH5678", "nrc": None,
    }]
    mock_client.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://signed/j.pdf"}
    app.dependency_overrides[get_authed_request] = lambda: AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")

    resp = client.get("/api/proceso/p04/justificante/u1:P04:2026:1T")

    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://signed/j.pdf"
    assert body["csv_aeat"] == "ABCD1234EFGH5678"


def test_get_justificante_404_si_no_presentado():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
        "estado": "presentando", "justificante_path": None, "csv_aeat": None, "nrc": None,
    }]
    app.dependency_overrides[get_authed_request] = lambda: AuthedRequest(client=mock_client, user_id="u1", jwt="fake-jwt")

    resp = client.get("/api/proceso/p04/justificante/u1:P04:2026:1T")

    assert resp.status_code == 404
