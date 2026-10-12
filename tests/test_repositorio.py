"""Pruebas del almacen con ciclo de vida y compuerta (F1-D03/V05/V07; H3, H4)."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.repositorio import (  # noqa: E402
    CONFIRMADO, EN_REVISION, OFICIAL, RECHAZADO, ErrorCicloDeVida, Repositorio,
    clave_registro)


def _df():
    return pd.DataFrame([
        {"prestador": "Enel", "servicio": "energia", "sede": "Campus", "factura": "F1",
         "periodo_fin": pd.Timestamp("2025-01-31"), "consumo": 100.0, "valor": 500.0,
         "estado": "OK", "archivo": "a.pdf"},
        {"prestador": "Enel", "servicio": "energia", "sede": "Campus", "factura": "F2",
         "periodo_fin": pd.Timestamp("2025-02-28"), "consumo": 900.0, "valor": 4500.0,
         "estado": "ATIPICO_REVISAR", "severidad": "ALTA", "detalle": "+800% vs 100",
         "archivo": "b.pdf"},
        {"prestador": "Enel", "servicio": "energia", "sede": "Campus", "factura": None,
         "periodo_fin": pd.Timestamp("2025-03-31"), "consumo": None, "valor": 10.0,
         "estado": "REVISION_BAJA_CONFIANZA", "archivo": "c.pdf"},
    ])


@pytest.fixture
def repo():
    r = Repositorio()
    r.cargar_validacion(_df(), run_id="run1")
    return r


def test_carga_separa_ok_de_marcadas(repo):
    assert repo.conteo() == {CONFIRMADO: 1, EN_REVISION: 2}


def test_compuerta_deja_fuera_lo_no_confirmado(repo):
    """H4: una fila marcada NO entra a la base oficial sin confirmacion."""
    repo.publicar_oficial()
    oficial = repo.exportar_oficial()
    assert list(oficial["factura"]) == ["F1"]
    assert repo.conteo()[EN_REVISION] == 2


def test_aprobar_permite_publicar(repo):
    cola = repo.cola_revision()
    atipica = int(cola[cola["factura"] == "F2"]["id"].iloc[0])
    repo.revisar(atipica, "Analista SGA", "APROBADO", observacion="obra en sede")
    repo.publicar_oficial()
    assert set(repo.exportar_oficial()["factura"]) == {"F1", "F2"}


def test_rechazar_nunca_llega_a_oficial(repo):
    cola = repo.cola_revision()
    rid = int(cola[cola["factura"] == "F2"]["id"].iloc[0])
    repo.revisar(rid, "Analista SGA", "RECHAZADO")
    repo.publicar_oficial()
    assert "F2" not in set(repo.exportar_oficial()["factura"])
    assert repo.conteo()[RECHAZADO] == 1


def test_correccion_guarda_original_y_nuevo(repo):
    """H3: toda modificacion deja quien, cuando, valor original y nuevo."""
    cola = repo.cola_revision()
    rid = int(cola[cola["factura"] == "F2"]["id"].iloc[0])
    repo.revisar(rid, "Analista SGA", "CORREGIDO", campo="consumo", valor_nuevo=90.0)
    h = repo.historial(rid).iloc[0]
    assert (h["revisor"], h["campo"], h["valor_original"], h["valor_nuevo"]) == (
        "Analista SGA", "consumo", "900.0", "90.0")
    assert h["fecha"]
    repo.publicar_oficial()
    ofi = repo.exportar_oficial()
    assert float(ofi[ofi["factura"] == "F2"]["consumo"].iloc[0]) == 90.0


def test_revisor_obligatorio_y_decision_valida(repo):
    rid = int(repo.cola_revision()["id"].iloc[0])
    with pytest.raises(ValueError):
        repo.revisar(rid, "", "APROBADO")
    with pytest.raises(ValueError):
        repo.revisar(rid, "x", "DUDOSO")
    with pytest.raises(ValueError):
        repo.revisar(rid, "x", "CORREGIDO", campo="consumo")  # sin valor nuevo
    with pytest.raises(ValueError):
        repo.revisar(rid, "x", "CORREGIDO", campo="archivo", valor_nuevo="z")
    assert repo.historial().empty  # nada de lo rechazado dejo rastro ni cambio


def test_registro_oficial_no_se_modifica(repo):
    repo.publicar_oficial()
    rid = int(repo.exportar_oficial()["id"].iloc[0])
    with pytest.raises(ErrorCicloDeVida):
        repo.revisar(rid, "Analista SGA", "CORREGIDO", campo="valor", valor_nuevo=1.0)
    assert repo.conteo()[OFICIAL] == 1


def test_recarga_es_idempotente_y_conserva_la_revision(repo):
    rid = int(repo.cola_revision()["id"].iloc[0])
    repo.revisar(rid, "Analista SGA", "APROBADO")
    r = repo.cargar_validacion(_df(), run_id="run2")
    assert r["nuevos"] == 0 and r["omitidos"] == 3
    assert repo.conteo()[EN_REVISION] == 1  # la aprobada no volvio a la cola


def test_auditoria_detecta_alteracion(repo):
    cola = repo.cola_revision()
    for rid in cola["id"]:
        repo.revisar(int(rid), "Analista SGA", "APROBADO")
    assert repo.verificar_auditoria() == []
    repo.con.execute("UPDATE revision SET revisor = 'otro' WHERE id = 1")
    assert repo.verificar_auditoria() != []


def test_clave_incluye_servicio_y_cae_a_archivo():
    a = {"prestador": "EPM", "servicio": "energia", "factura": "9"}
    b = {"prestador": "EPM", "servicio": "acueducto", "factura": "9"}
    assert clave_registro(a) != clave_registro(b)
    sin_nro = {"prestador": "EAAB", "servicio": "acueducto", "factura": None,
               "archivo": "1. ENERO.2026.pdf"}
    # Mismo nombre de archivo en sedes distintas: no deben colisionar.
    assert clave_registro({**sin_nro, "sede": "Campus"}) != clave_registro(
        {**sin_nro, "sede": "Calle 84"})
