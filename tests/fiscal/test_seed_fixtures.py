"""Sanity checks on the seed fixtures themselves. Acceptance criteria: CA-F1-05."""
from tests.fixtures.facturas import todas_las_facturas_emitidas, todas_las_facturas_recibidas


def test_seed_emitidas_minimo_10_y_tipos_variados():
    emitidas = todas_las_facturas_emitidas()
    assert len(emitidas) >= 10
    tipos = {f.tipo_iva for f in emitidas}
    assert tipos == {0, 10, 21}


def test_seed_recibidas_minimo_8_categorias_distintas():
    recibidas = todas_las_facturas_recibidas()
    assert len(recibidas) >= 8
    categorias = {f.categoria_gasto for f in recibidas}
    assert len(categorias) >= 3  # corriente-style categories + inversión + ISP
    assert any(f.es_isp for f in recibidas)
    assert any(f.es_bien_inversion for f in recibidas)


def test_seed_al_menos_una_factura_con_retencion_irpf():
    emitidas = todas_las_facturas_emitidas()
    assert any(f.retencion_irpf > 0 for f in emitidas)
