"""Pruebas de la carga incremental: deteccion por contenido, registro por hash y exportacion."""
import shutil

import fitz
import pandas as pd
import pytest

from src.processor import carga, extraccion
from src.processor.extraccion import OK, OMITIDA, PENDIENTE


def _pdf(ruta, texto):
    doc = fitz.open()
    doc.new_page().insert_textbox(fitz.Rect(30, 30, 560, 800), texto)
    doc.save(str(ruta))
    doc.close()


def _falso_ok(ruta, ocr=None, origen=None):
    return {"archivo": ruta.split("\\")[-1].split("/")[-1], "ruta": ruta, "origen": "prueba",
            "estado": OK, "motivo": "", "prestador": "Enel", "via_ocr": False,
            "filas": [{"hoja": "Energia", "datos": {"archivo_origen": "f.pdf", "consumo_kwh": 10}}]}


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "registro.db")


@pytest.mark.parametrize("texto,esperado", [
    ("Factura Enel Colombia cliente 123", "enel"),
    ("EMPRESA DE ACUEDUCTO Y ALCANTARILLADO DE BOGOTA EAAB", "eaab"),
    ("Recibo EMCALI servicios", "emcali"),
    ("Empresas Varias de Medellin Emvarias aseo", "aseo"),
    ("documento cualquiera sin prestador conocido", None),
])
def test_detectar_prestador(texto, esperado):
    assert extraccion.detectar_prestador(texto) == esperado


def test_pdf_desconocido_es_pendiente_con_motivo_legible(tmp_path):
    _pdf(tmp_path / "x.pdf", "Este documento no es una factura de servicios publicos conocida. " * 12)
    res = extraccion.extraer_pdf(str(tmp_path / "x.pdf"))
    assert res["estado"] == PENDIENTE and "no reconocido" in res["motivo"]


def test_pdf_aseo_queda_fuera_de_alcance(tmp_path):
    _pdf(tmp_path / "a.pdf", "Emvarias Empresas Varias de Medellin total aseo del periodo facturado")
    assert extraccion.extraer_pdf(str(tmp_path / "a.pdf"))["estado"] == OMITIDA


def test_pdf_corrupto_no_detiene_el_proceso(tmp_path):
    (tmp_path / "roto.pdf").write_bytes(b"no soy un pdf")
    res = extraccion.extraer_pdf(str(tmp_path / "roto.pdf"))
    assert res["estado"] == "ERROR" and res["motivo"]


def test_expandir_rutas_recursivo_y_solo_pdf(tmp_path):
    (tmp_path / "sub").mkdir()
    _pdf(tmp_path / "sub" / "a.pdf", "x")
    (tmp_path / "notas.txt").write_text("hola")
    pdfs, ignorados = carga.expandir_rutas([str(tmp_path)])
    assert len(pdfs) == 1 and len(ignorados) == 1


def test_incremental_no_repite_lo_cargado(tmp_path, db, monkeypatch):
    monkeypatch.setattr(carga, "extraer_pdf", _falso_ok)
    _pdf(tmp_path / "a.pdf", "factura uno")
    r1 = carga.procesar([str(tmp_path)], db=db)
    assert (r1["leidas"], r1["ok"]) == (1, 1)
    _pdf(tmp_path / "b.pdf", "factura dos")
    r2 = carga.procesar([str(tmp_path)], db=db)
    assert (r2["leidas"], r2["omitidas"]) == (1, 1)          # solo la nueva
    assert carga.procesar([str(tmp_path)], db=db, forzar=True)["leidas"] == 2


def test_mismo_contenido_con_otro_nombre_es_repetido(tmp_path, db, monkeypatch):
    monkeypatch.setattr(carga, "extraer_pdf", _falso_ok)
    _pdf(tmp_path / "a.pdf", "factura uno")
    shutil.copy(tmp_path / "a.pdf", tmp_path / "copia.pdf")
    plan = carga.planificar([str(tmp_path)], db=db)
    assert len(plan["nuevos"]) == 1 and len(plan["repetidos_en_seleccion"]) == 1
    carga.procesar([str(tmp_path)], db=db)
    assert len(carga.planificar([str(tmp_path)], db=db)["ya_cargados"]) == 1


def test_cambio_de_version_reprocesa(tmp_path, db, monkeypatch):
    monkeypatch.setattr(carga, "extraer_pdf", _falso_ok)
    _pdf(tmp_path / "a.pdf", "factura uno")
    carga.procesar([str(tmp_path)], db=db)
    monkeypatch.setattr(carga, "VERSION_EXTRACTORES", "otra-version")
    assert len(carga.planificar([str(tmp_path)], db=db)["reprocesar"]) == 1


def test_exportar_extraccion_acumula_y_separa_pendientes(tmp_path, db, monkeypatch):
    _pdf(tmp_path / "a.pdf", "factura uno")
    _pdf(tmp_path / "b.pdf", "no reconocible " * 10)
    monkeypatch.setattr(carga.rutas, "ultimo", lambda patron: None)
    monkeypatch.setattr(carga, "extraer_pdf", lambda r, o=None, g=None: (
        _falso_ok(r) if r.endswith("a.pdf") else extraccion.extraer_pdf(r)))
    carga.procesar([str(tmp_path)], db=db)
    salida = carga.exportar_extraccion(db=db, destino=str(tmp_path / "out.xlsx"))
    libro = pd.read_excel(salida, sheet_name=None)
    assert len(libro["Energia"]) == 1 and len(libro["Pendientes"]) == 1


def test_exportar_sin_datos_devuelve_none(db, monkeypatch):
    monkeypatch.setattr(carga.rutas, "ultimo", lambda patron: None)
    assert carga.exportar_extraccion(db=db) is None


def test_exportar_incluye_lotes_historicos(tmp_path, db, monkeypatch):
    """Lo extraido antes con los scripts por lote no desaparece al usar la app."""
    lote = tmp_path / "bogota_x.xlsx"
    with pd.ExcelWriter(lote) as w:
        pd.DataFrame([{"archivo_origen": "viejo.pdf", "consumo_kwh": 5}]).to_excel(w, sheet_name="Energia", index=False)
    monkeypatch.setattr(carga.rutas, "ultimo", lambda patron: str(lote) if patron.startswith("bogota") else None)
    monkeypatch.setattr(carga, "extraer_pdf", _falso_ok)
    _pdf(tmp_path / "a.pdf", "factura uno")
    carga.procesar([str(tmp_path / "a.pdf")], db=db)
    libro = pd.read_excel(carga.exportar_extraccion(db=db, destino=str(tmp_path / "o.xlsx")), sheet_name="Energia")
    assert set(libro["archivo_origen"]) == {"f.pdf", "viejo.pdf"}
    solo_app = pd.read_excel(carga.exportar_extraccion(db=db, destino=str(tmp_path / "p.xlsx"),
                                                       incluir_historico=False), sheet_name="Energia")
    assert set(solo_app["archivo_origen"]) == {"f.pdf"}


def test_dashboard_sin_correos_no_bloquea_la_actualizacion(monkeypatch):
    """Si publicar_dashboard falla (sin correos autorizados) el Excel igual queda actualizado."""
    from types import SimpleNamespace
    from src.processor import actualizacion

    monkeypatch.setattr(actualizacion.carga, "exportar_extraccion", lambda: "x.xlsx")
    monkeypatch.setattr(actualizacion, "copiar_dashboard_local", lambda: False)

    def falso_run(cmd, **kw):
        if "publicar_dashboard.py" in cmd[-1]:
            return SimpleNamespace(returncode=1, stdout="Sin correos autorizados. Agregue uno", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(actualizacion.subprocess, "run", falso_run)
    res = actualizacion.actualizar()
    assert res["ok"] and len(res["avisos"]) == 1 and "correos autorizados" in res["avisos"][0]


def test_etapa_obligatoria_que_falla_si_detiene(monkeypatch):
    from types import SimpleNamespace
    from src.processor import actualizacion

    monkeypatch.setattr(actualizacion.carga, "exportar_extraccion", lambda: "x.xlsx")
    monkeypatch.setattr(actualizacion.subprocess, "run",
                        lambda cmd, **kw: SimpleNamespace(returncode=1, stdout="", stderr="boom"))
    res = actualizacion.actualizar()
    assert not res["ok"] and "boom" in res["detalle"]


def _pdf_imagen(ruta):
    """PDF sin texto extraible (solo una imagen), como un escaneo."""
    doc = fitz.open()
    pagina = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), False)
    pix.clear_with(200)
    pagina.insert_image(fitz.Rect(50, 50, 200, 200), pixmap=pix)
    doc.save(str(ruta))
    doc.close()


def test_escaneado_sin_tesseract_da_mensaje_claro(tmp_path, monkeypatch):
    monkeypatch.setattr(extraccion, "buscar_tesseract", lambda: None)
    _pdf_imagen(tmp_path / "scan.pdf")
    res = extraccion.extraer_pdf(str(tmp_path / "scan.pdf"))
    assert res["estado"] == "ERROR" and "no tiene Tesseract" in res["motivo"] and "Instalar.bat" in res["motivo"]


def test_escaneado_sin_idioma_espanol_da_mensaje_claro(tmp_path, monkeypatch):
    falso_exe = tmp_path / "tesseract.exe"
    falso_exe.write_text("x")
    monkeypatch.setattr(extraccion, "buscar_tesseract", lambda: str(falso_exe))
    monkeypatch.setattr(extraccion, "BASE", str(tmp_path))          # sin config/tessdata
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    _pdf_imagen(tmp_path / "scan.pdf")
    res = extraccion.extraer_pdf(str(tmp_path / "scan.pdf"))
    assert res["estado"] == "ERROR" and "idioma español" in res["motivo"]


def test_buscar_tesseract_encuentra_la_variable_de_entorno(tmp_path, monkeypatch):
    exe = tmp_path / "tesseract.exe"
    exe.write_text("x")
    monkeypatch.setenv("TESSERACT_PATH", str(exe))
    assert extraccion.buscar_tesseract() == str(exe)


def test_factura_digital_no_necesita_tesseract(tmp_path, monkeypatch):
    monkeypatch.setattr(extraccion, "buscar_tesseract", lambda: None)
    _pdf(tmp_path / "a.pdf", "Emvarias Empresas Varias de Medellin total aseo del periodo facturado")
    assert extraccion.extraer_pdf(str(tmp_path / "a.pdf"))["estado"] == OMITIDA
