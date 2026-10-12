/* Dashboard del Monitor de Consumos Ambientales (sitio estatico cifrado).
 *
 * Los datos se descifran en el navegador (descifrar.js) y viven solo en memoria.
 * Interaccion: los filtros y los graficos (Apache ECharts, local) se filtran entre si; un clic en
 * una barra de sede, en un mes o en una porcion del estado filtra todo el tablero.
 * Todo texto proveniente de las facturas se inserta con textContent (datos no
 * confiables): nunca como HTML. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const TODOS = "(todos)";
  const fmt = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
  const fmtPct = (v) => `${(v * 100).toFixed(0)} %`;
  const fmtMoneda = new Intl.NumberFormat("es-CO", {
    style: "currency", currency: "COP", maximumFractionDigits: 0 });
  const POR_PAGINA = 25;
  const META_AUTOMATIZACION = 0.8, MINIMO_AUTOMATIZACION = 0.6;

  // Estado de validacion -> [etiqueta, variable de color]
  const ESTADOS = {
    OK: ["Sin hallazgos", "--ok"],
    ATIPICO_REVISAR: ["Atípico", "--media"],
    SIN_SERIE: ["Sin medidor", "--neutro"],
    REVISION_BAJA_CONFIANZA: ["Baja confianza", "--alta"],
    REVISION_PERIODO_INFERIDO: ["Periodo inferido", "--info"],
    REVISION_UNIDAD: ["Unidad incoherente", "--info"],
  };
  const etiquetaEstado = (e) => (ESTADOS[e] ? ESTADOS[e][0] : e || "—");

  let datos = null;
  let vista = "ejecutiva";
  let tab = "cola";
  let unidadSede = "kWh";
  const pag = { cola: 0, facturas: 0 };
  // Filtros globales. desde/hasta = "AAAA-MM". estado se fija desde el grafico.
  const F = { servicio: TODOS, sede: TODOS, prestador: TODOS, desde: TODOS, hasta: TODOS, estado: TODOS };
  let hallazgo = TODOS;

  // ---------- utilidades DOM ----------
  function el(tag, texto, clase) {
    const e = document.createElement(tag);
    if (texto !== undefined && texto !== null) e.textContent = String(texto);
    if (clase) e.className = clase;
    return e;
  }
  function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const sumar = (filas, campo) => filas.reduce((a, f) => a + (Number(f[campo]) || 0), 0);
  const contar = (filas, campo) => filas.reduce((m, f) => { m[f[campo]] = (m[f[campo]] || 0) + 1; return m; }, {});

  // ---------- login ----------
  async function ingresar(evento) {
    evento.preventDefault();
    const msg = $("msg-login"), boton = $("entrar");
    msg.hidden = true;
    boton.disabled = true;
    boton.textContent = "Verificando…";
    try {
      const respuesta = await fetch("data.enc.json", { cache: "no-store" });
      if (!respuesta.ok) throw new Error("lectura");
      datos = await window.Descifrar.descifrar(
        await respuesta.json(), $("correo").value, $("clave").value);
      $("clave").value = "";
      $("login").hidden = true;
      $("app").hidden = false;
      iniciar();
    } catch (e) {
      msg.textContent = e.message === "credenciales"
        ? "Correo o contraseña incorrectos."
        : "No se pudo abrir el tablero. Intente de nuevo.";
      msg.hidden = false;
    } finally {
      boton.disabled = false;
      boton.textContent = "Ingresar";
    }
  }

  function salir() {
    Object.keys(instancias).forEach((id) => { instancias[id].dispose(); delete instancias[id]; });
    datos = null;
    $("app").hidden = true;
    $("login").hidden = false;
    $("correo").focus();
  }

  // ---------- filtros ----------
  function llenar(id, valores, etiquetas) {
    const s = $(id), previo = s.value;
    vaciar(s);
    [TODOS, ...valores].forEach((v) => {
      const o = el("option", v === TODOS ? v : (etiquetas ? etiquetas(v) : v));
      o.value = v;
      s.appendChild(o);
    });
    s.value = valores.includes(previo) ? previo : TODOS;
  }
  const unicos = (campo) => [...new Set(datos.facturas.map((f) => f[campo]).filter(Boolean))].sort();

  function pasa(r, sinTiempo) {
    return (F.servicio === TODOS || r.servicio === F.servicio) &&
      (F.sede === TODOS || r.sede === F.sede) &&
      (F.prestador === TODOS || r.prestador === F.prestador) &&
      (F.estado === TODOS || r.estado === F.estado) &&
      (sinTiempo || ((F.desde === TODOS || (r.ymes && r.ymes >= F.desde)) &&
                     (F.hasta === TODOS || (r.ymes && r.ymes <= F.hasta))));
  }
  const filtradas = (sinTiempo) => datos.facturas.filter((r) => pasa(r, sinTiempo));

  function sincronizarSelects() {
    $("f-servicio").value = F.servicio;
    $("f-sede").value = F.sede;
    $("f-prestador").value = F.prestador;
    $("f-desde").value = F.desde;
    $("f-hasta").value = F.hasta;
  }

  function fijar(clave, valor) {
    // Un segundo clic sobre el mismo valor lo quita (alternar).
    F[clave] = F[clave] === valor ? TODOS : valor;
    pag.cola = 0; pag.facturas = 0;
    sincronizarSelects();
    renderizar();
  }

  function chips() {
    const caja = $("chips");
    vaciar(caja);
    const etiquetas = {
      servicio: "Servicio", sede: "Sede", prestador: "Prestador", desde: "Desde", hasta: "Hasta", estado: "Estado" };
    let activos = 0;
    Object.keys(F).forEach((k) => {
      if (F[k] === TODOS) return;
      activos += 1;
      const c = el("span", null, "chip");
      c.appendChild(el("span", `${etiquetas[k]}: ${k === "estado" ? etiquetaEstado(F[k]) : F[k]}`));
      const x = el("button", "×");
      x.type = "button";
      x.setAttribute("aria-label", `Quitar filtro ${etiquetas[k]}`);
      x.addEventListener("click", () => { F[k] = TODOS; sincronizarSelects(); renderizar(); });
      c.appendChild(x);
      caja.appendChild(c);
    });
    $("limpiar").hidden = activos === 0;
  }

  function iniciar() {
    $("meta").textContent =
      `Datos generados el ${datos.generado} · fuente ${datos.fuente} · ${datos.facturas.length} filas`;
    Object.keys(F).forEach((k) => { F[k] = TODOS; });
    hallazgo = TODOS;
    pag.cola = 0; pag.facturas = 0;
    llenar("f-servicio", unicos("servicio"));
    llenar("f-sede", unicos("sede"));
    llenar("f-prestador", unicos("prestador"));
    const meses = unicos("ymes");
    llenar("f-desde", meses);
    llenar("f-hasta", meses);
    llenar("f-hallazgo", ["ALTA", "MEDIA", "SIN_SERIE", "REVISION_BAJA_CONFIANZA",
      "REVISION_PERIODO_INFERIDO", "REVISION_UNIDAD"], (v) =>
      v === "ALTA" ? "Atípico · severidad alta" : v === "MEDIA" ? "Atípico · severidad media" : etiquetaEstado(v));
    renderizar();
  }

  // ---------- render ----------
  function renderizar() {
    if (!datos) return;
    chips();
    if (vista === "ejecutiva") ejecutiva(); else operativa();
  }

  // ===== EJECUTIVA =====
  function ejecutiva() {
    const filas = filtradas(false);
    aviso();
    kpisEjecutivos(filas);
    graficoMensual("g-energia", "kWh", css("--acento"));
    graficoMensual("g-agua", "m3", css("--agua"));
    graficoSedes(filas);
    calidad(filas);
    semaforo(filas);
  }

  function aviso() {
    const caja = $("aviso");
    const atip = datos.facturas.filter((r) => r.estado === "ATIPICO_REVISAR");
    const med3 = atip.filter((r) => (r.detalle || "").includes("(mediana3)")).length;
    if (atip.length && med3 / atip.length > 0.5) {
      caja.textContent =
        `${fmt.format(med3)} de ${fmt.format(atip.length)} atípicos se calcularon con la mediana de los 3 periodos previos, ` +
        "porque aún no hay 12 meses de histórico. Úselos para priorizar la revisión, no como diagnóstico.";
      caja.hidden = false;
    } else {
      caja.hidden = true;
    }
  }

  function kpiCaja(titulo, valor, sub, clase, unidad) {
    const k = el("div", null, "kpi" + (clase ? " " + clase : ""));
    k.appendChild(el("div", titulo, "suave pequeno"));
    const v = el("div", valor, "valor");
    if (unidad) v.appendChild(el("span", " " + unidad, "unidad"));
    k.appendChild(v);
    if (sub) k.appendChild(el("div", sub, "sub"));
    return k;
  }

  function kpisEjecutivos(filas) {
    const caja = $("kpis-ej");
    vaciar(caja);
    const total = filas.length;
    const ok = filas.filter((r) => r.estado === "OK").length;
    const pct = total ? ok / total : 0;
    const altas = filas.filter((r) => r.severidad === "ALTA" && r.estado === "ATIPICO_REVISAR").length;
    const falt = datos.faltantes.filter((x) => F.servicio === TODOS || x.servicio === F.servicio).length;
    caja.appendChild(kpiCaja("Energía", fmt.format(sumar(filas.filter((r) => r.unidad === "kWh"), "consumo")), `${fmt.format(filas.filter((r) => r.unidad === "kWh").length)} facturas`, "", "kWh"));
    caja.appendChild(kpiCaja("Agua", fmt.format(sumar(filas.filter((r) => r.unidad === "m3"), "consumo")), `${fmt.format(filas.filter((r) => r.unidad === "m3").length)} facturas`, "", "m³"));
    caja.appendChild(kpiCaja("Valor facturado", fmtMoneda.format(sumar(filas, "valor")), `${fmt.format(total)} facturas`));

    const auto = kpiCaja("Facturas sin revisión manual", fmtPct(pct),
      `Meta ${fmtPct(META_AUTOMATIZACION)} · mínimo ${fmtPct(MINIMO_AUTOMATIZACION)}`,
      pct < MINIMO_AUTOMATIZACION && total ? "alerta" : "");
    const barra = el("div", null, "barra-prog");
    const relleno = el("span");
    relleno.style.width = `${Math.min(100, pct * 100)}%`;
    barra.appendChild(relleno);
    [MINIMO_AUTOMATIZACION, META_AUTOMATIZACION].forEach((m) => {
      const marca = el("i");
      marca.style.left = `${m * 100}%`;
      barra.appendChild(marca);
    });
    auto.insertBefore(barra, auto.querySelector(".sub"));
    caja.appendChild(auto);

    caja.appendChild(kpiCaja("Atípicos severidad alta", fmt.format(altas), "por revisar", altas ? "alerta" : ""));
    caja.appendChild(kpiCaja("Posibles faltantes", fmt.format(falt), "facturas esperadas", falt ? "alerta" : ""));
  }

  // ---------- graficos (Apache ECharts, servido desde el propio sitio) ----------
  const instancias = {};     // id -> instancia de ECharts
  const mesesDe = {};        // id -> meses del ultimo render (para el clic)
  const compacto = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });
  const ENTIDADES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const escapar = (t) => String(t).replace(/[&<>"']/g, (c) => ENTIDADES[c]);

  function instancia(id) {
    const nodo = $(id);
    if (!window.echarts) {
      vaciar(nodo);
      nodo.appendChild(el("p", "No se pudo cargar la librería de gráficos.", "vacio"));
      return null;
    }
    if (!instancias[id]) {
      instancias[id] = window.echarts.init(nodo, null, { renderer: "canvas" });
      instancias[id].on("click", (p) => {
        const meses = mesesDe[id];
        if (meses && meses[p.dataIndex] !== undefined) fijarMes(meses[p.dataIndex]);
      });
    }
    return instancias[id];
  }

  // Serie mensual: ignora el filtro de periodo (conserva el contexto) y resalta el rango elegido.
  function graficoMensual(id, unidad, color) {
    const filas = filtradas(true).filter((r) => r.unidad === unidad && r.ymes);
    const nodo = $(id);
    const por = {}, medidores = {};
    filas.forEach((r) => {
      por[r.ymes] = (por[r.ymes] || 0) + (Number(r.consumo) || 0);
      (medidores[r.ymes] = medidores[r.ymes] || new Set()).add(r.cuenta || r.direccion || r.archivo);
    });
    const meses = Object.keys(por).sort();
    if (!meses.length) {
      if (instancias[id]) { instancias[id].dispose(); delete instancias[id]; }
      vaciar(nodo);
      nodo.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio"));
      return;
    }
    if (nodo.querySelector(".vacio")) vaciar(nodo);
    const chart = instancia(id);
    if (!chart) return;
    mesesDe[id] = meses;
    const maxMed = Math.max(1, ...meses.map((m) => medidores[m].size));
    const enRango = (m) => (F.desde === TODOS || m >= F.desde) && (F.hasta === TODOS || m <= F.hasta);
    const u = unidad === "kWh" ? "kWh" : "m³";
    const texto = css("--texto"), suave = css("--suave"), borde = css("--borde");
    chart.setOption({
      animationDuration: 400,
      textStyle: { color: texto },
      grid: { left: 52, right: 16, top: 16, bottom: 64 },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        backgroundColor: css("--tarjeta"), borderColor: borde, textStyle: { color: texto },
        formatter: (ps) => {
          const m = meses[ps[0].dataIndex];
          const parcial = medidores[m].size / maxMed < 0.6 ? "<br><i>Cobertura parcial del mes</i>" : "";
          return `<b>${escapar(m)}</b><br>${fmt.format(por[m])} ${u}<br>${medidores[m].size} medidores con factura${parcial}`;
        },
      },
      xAxis: { type: "category", data: meses, axisLabel: { color: suave, rotate: meses.length > 8 ? 45 : 0 },
        axisLine: { lineStyle: { color: borde } }, axisTick: { show: false } },
      yAxis: { type: "value", axisLabel: { color: suave, formatter: (v) => compacto.format(v) },
        splitLine: { lineStyle: { color: borde } } },
      // La rueda sola desplaza la pagina; el zoom con la rueda exige Ctrl.
      dataZoom: [{ type: "inside", zoomOnMouseWheel: "ctrl", moveOnMouseWheel: false,
        moveOnMouseMove: false, preventDefaultMouseMove: false }, { type: "slider", height: 16, bottom: 6, borderColor: borde,
        fillerColor: "rgba(120,140,160,.18)", textStyle: { color: suave }, brushSelect: false }],
      series: [{
        type: "bar", cursor: "pointer", barMaxWidth: 34,
        itemStyle: { color, borderRadius: [4, 4, 0, 0] },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,.25)" } },
        data: meses.map((m) => ({
          value: por[m],
          itemStyle: { opacity: (enRango(m) ? 1 : 0.28) * (medidores[m].size / maxMed < 0.6 ? 0.6 : 1) },
        })),
      }],
    }, true);
    chart.resize();
  }

  function fijarMes(mes) {
    if (F.desde === mes && F.hasta === mes) { F.desde = TODOS; F.hasta = TODOS; }
    else { F.desde = mes; F.hasta = mes; }
    pag.cola = 0; pag.facturas = 0;
    sincronizarSelects();
    renderizar();
  }

  // Ranking de sedes en HTML: cada fila es un boton que filtra por esa sede.
  function graficoSedes(filas) {
    const unidad = unidadSede === "kWh" ? "kWh" : "m³";
    $("t-sede").textContent = `Sedes con mayor consumo (${unidad})`;
    const por = {};
    filas.filter((r) => r.unidad === unidadSede).forEach((r) => {
      por[r.sede] = (por[r.sede] || 0) + (Number(r.consumo) || 0);
    });
    const items = Object.entries(por).sort((a, b) => b[1] - a[1]);
    const total = items.reduce((a, i) => a + i[1], 0) || 1;
    const max = items.length ? items[0][1] : 1;
    const caja = $("g-sede");
    vaciar(caja);
    if (!items.length) { caja.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio")); return; }
    const lista = el("div", null, "ranking");
    items.slice(0, 12).forEach(([sede, valor], i) => {
      const fila = el("button", null, "rank-fila");
      fila.type = "button";
      fila.setAttribute("aria-pressed", String(F.sede === sede));
      fila.title = `${sede}: ${fmt.format(valor)} ${unidad} (${fmtPct(valor / total)})`;
      fila.appendChild(el("span", i + 1, "rank-n"));
      const cuerpo = el("span", null, "rank-cuerpo");
      cuerpo.appendChild(el("span", sede, "rank-nombre"));
      const pista = el("span", null, "rank-pista");
      const barra = el("span", null, unidadSede === "m3" ? "rank-barra agua" : "rank-barra");
      barra.style.width = `${Math.max(2, (valor / max) * 100)}%`;
      pista.appendChild(barra);
      cuerpo.appendChild(pista);
      fila.appendChild(cuerpo);
      const num = el("span", null, "rank-valor");
      num.appendChild(el("strong", fmt.format(valor)));
      num.appendChild(el("small", fmtPct(valor / total)));
      fila.appendChild(num);
      if (sede !== "SIN_MAPEO") fila.addEventListener("click", () => fijar("sede", sede));
      else fila.disabled = true;
      lista.appendChild(fila);
    });
    caja.appendChild(lista);
  }

  // Calidad de los datos: barra apilada + leyenda clicable (filtra por estado).
  function calidad(filas) {
    const cuenta = contar(filas, "estado");
    const claves = Object.keys(cuenta).sort((a, b) => cuenta[b] - cuenta[a]);
    const total = filas.length;
    const sinSede = filas.filter((r) => r.sede === "SIN_MAPEO").length;
    $("sin-sede").textContent = sinSede
      ? `${fmt.format(sinSede)} facturas (${fmtPct(sinSede / total)}) sin sede identificada: no aparecen en el ranking ni en el semáforo.`
      : "";
    const caja = $("g-estado");
    vaciar(caja);
    if (!total) { caja.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio")); return; }
    const barra = el("div", null, "apilada");
    barra.setAttribute("role", "img");
    barra.setAttribute("aria-label", "Distribución de facturas por estado de validación");
    claves.forEach((k) => {
      const seg = el("span");
      seg.style.width = `${(cuenta[k] / total) * 100}%`;
      seg.style.background = css(ESTADOS[k] ? ESTADOS[k][1] : "--neutro");
      seg.title = `${etiquetaEstado(k)}: ${cuenta[k]} (${fmtPct(cuenta[k] / total)})`;
      barra.appendChild(seg);
    });
    caja.appendChild(barra);
    const leyenda = el("div", null, "leyenda");
    claves.forEach((k) => {
      const fila = el("button", null, "ley-fila");
      fila.type = "button";
      fila.setAttribute("aria-pressed", String(F.estado === k));
      const punto = el("span", null, "ley-punto");
      punto.style.background = css(ESTADOS[k] ? ESTADOS[k][1] : "--neutro");
      fila.appendChild(punto);
      fila.appendChild(el("span", etiquetaEstado(k), "ley-nombre"));
      fila.appendChild(el("strong", fmt.format(cuenta[k])));
      fila.appendChild(el("small", fmtPct(cuenta[k] / total)));
      fila.addEventListener("click", () => fijar("estado", k));
      leyenda.appendChild(fila);
    });
    caja.appendChild(leyenda);
  }

  // Semaforo por sede: una tarjeta por sede, ordenadas por criticidad.
  function semaforo(filas) {
    const por = {};
    filas.forEach((r) => {
      const s = (por[r.sede] = por[r.sede] || { n: 0, ok: 0, atip: 0, alta: 0, kwh: 0, m3: 0 });
      s.n += 1;
      if (r.estado === "OK") s.ok += 1;
      if (r.estado === "ATIPICO_REVISAR") { s.atip += 1; if (r.severidad === "ALTA") s.alta += 1; }
      if (r.unidad === "kWh") s.kwh += Number(r.consumo) || 0;
      if (r.unidad === "m3") s.m3 += Number(r.consumo) || 0;
    });
    const rango = { Crítico: 0, Atención: 1, Normal: 2 };
    const nivel = (s) => (s.alta >= 3 ? "Crítico" : (s.atip > 0 || s.ok / s.n < 0.6 ? "Atención" : "Normal"));
    const lista = Object.entries(por).map(([sede, s]) => ({ sede, ...s, nivel: nivel(s) }))
      .sort((a, b) => rango[a.nivel] - rango[b.nivel] || b.alta - a.alta || b.n - a.n);
    const caja = $("t-semaforo");
    vaciar(caja);
    if (!lista.length) { caja.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio")); return; }
    const rejilla = el("div", null, "tiles");
    lista.forEach((r) => {
      const t = el("button", null, "tile " + r.nivel);
      t.type = "button";
      t.setAttribute("aria-pressed", String(F.sede === r.sede));
      t.appendChild(el("span", r.nivel, "sem " + r.nivel));
      t.appendChild(el("span", r.sede, "tile-nombre"));
      const datosT = el("span", null, "tile-datos");
      [["Facturas", fmt.format(r.n)], ["kWh", fmt.format(r.kwh)], ["m³", fmt.format(r.m3)],
        ["Atípicos", r.atip ? `${r.atip}${r.alta ? ` (${r.alta} altos)` : ""}` : "0"]].forEach(([k, v]) => {
        const c = el("span");
        c.appendChild(el("small", k));
        c.appendChild(el("strong", v));
        datosT.appendChild(c);
      });
      t.appendChild(datosT);
      const m = el("span", null, "mini ancho"), bb = el("span");
      bb.style.width = `${Math.round((r.ok / r.n) * 100)}%`;
      m.appendChild(bb);
      t.appendChild(m);
      t.appendChild(el("small", `${fmtPct(r.ok / r.n)} sin hallazgos`, "suave"));
      if (r.sede !== "SIN_MAPEO") t.addEventListener("click", () => fijar("sede", r.sede));
      else t.disabled = true;
      rejilla.appendChild(t);
    });
    caja.appendChild(rejilla);
  }

  // ===== OPERATIVA =====
  function operativa() {
    resumenCola();
    if (tab === "cola") cola();
    if (tab === "faltantes") faltantes();
    if (tab === "facturas") facturas();
    if (tab === "prestadores") prestadores();
  }

  const esAtipico = (r) => r.estado === "ATIPICO_REVISAR";
  function coincideHallazgo(r) {
    if (hallazgo === TODOS) return r.estado !== "OK";
    if (hallazgo === "ALTA" || hallazgo === "MEDIA") return esAtipico(r) && r.severidad === hallazgo;
    return r.estado === hallazgo;
  }

  function resumenCola() {
    const filas = filtradas(false);
    const caja = $("cola-resumen");
    vaciar(caja);
    const items = [
      [TODOS, "Por revisar", filas.filter((r) => r.estado !== "OK").length],
      ["ALTA", "Atípicos · alta", filas.filter((r) => esAtipico(r) && r.severidad === "ALTA").length],
      ["MEDIA", "Atípicos · media", filas.filter((r) => esAtipico(r) && r.severidad === "MEDIA").length],
      ["SIN_SERIE", "Sin medidor", filas.filter((r) => r.estado === "SIN_SERIE").length],
      ["REVISION_BAJA_CONFIANZA", "Baja confianza", filas.filter((r) => r.estado === "REVISION_BAJA_CONFIANZA").length],
    ];
    items.forEach(([clave, titulo, n]) => {
      const b = el("button", null, "kpi clic");
      b.type = "button";
      b.setAttribute("aria-pressed", String(hallazgo === clave));
      b.appendChild(el("div", titulo, "suave pequeno"));
      b.appendChild(el("div", fmt.format(n), "valor"));
      b.addEventListener("click", () => {
        hallazgo = hallazgo === clave ? TODOS : clave;
        $("f-hallazgo").value = hallazgo;
        pag.cola = 0;
        renderizar();
      });
      caja.appendChild(b);
    });
    const f = el("div", null, "kpi");
    f.appendChild(el("div", "Faltantes", "suave pequeno"));
    f.appendChild(el("div", fmt.format(datos.faltantes.length), "valor"));
    caja.appendChild(f);
  }

  const orden = { ALTA: 0, MEDIA: 1 };
  function buscar(filas, q) {
    q = (q || "").trim().toLowerCase();
    if (!q) return filas;
    return filas.filter((r) => [r.factura, r.sede, r.archivo, r.prestador, r.cuenta, r.direccion]
      .some((v) => v && String(v).toLowerCase().includes(q)));
  }
  const colConsumo = { t: "Consumo", v: (r) => `${r.consumo === null ? "" : fmt.format(r.consumo)} ${r.unidad || ""}`, num: true };

  function paginar(lista, clave, infoId, antId, sigId) {
    const paginas = Math.max(1, Math.ceil(lista.length / POR_PAGINA));
    pag[clave] = Math.min(pag[clave], paginas - 1);
    $(infoId).textContent = `${fmt.format(lista.length)} filas · página ${pag[clave] + 1} de ${paginas}`;
    $(antId).disabled = pag[clave] === 0;
    $(sigId).disabled = pag[clave] >= paginas - 1;
    return lista.slice(pag[clave] * POR_PAGINA, (pag[clave] + 1) * POR_PAGINA);
  }

  function cola() {
    const lista = buscar(filtradas(false).filter(coincideHallazgo), $("buscar-cola").value)
      .sort((a, b) => (orden[a.severidad] ?? 2) - (orden[b.severidad] ?? 2) ||
        String(b.periodo_fin).localeCompare(String(a.periodo_fin)));
    const visibles = paginar(lista, "cola", "cola-info", "cola-ant", "cola-sig");
    const caja = $("t-cola");
    vaciar(caja);
    caja.appendChild(tabla([
      { t: "Hallazgo", v: (r) => (esAtipico(r) ? `Atípico ${(r.severidad || "").toLowerCase()}` : etiquetaEstado(r.estado)), tipo: "etq" },
      { t: "Sede", v: (r) => r.sede },
      { t: "Servicio", v: (r) => r.servicio },
      { t: "Periodo", v: (r) => r.periodo_fin },
      { t: "Factura", v: (r) => r.factura },
      colConsumo,
      { t: "Detalle", v: (r) => r.detalle },
    ], visibles, "Sin hallazgos para los filtros elegidos.", abrirDetalle));
  }

  function faltantes() {
    const lista = datos.faltantes.filter((x) => F.servicio === TODOS || x.servicio === F.servicio);
    const caja = $("t-faltantes");
    vaciar(caja);
    caja.appendChild(tabla([
      { t: "Tipo", v: (r) => (r.tipo === "HUECO_EN_SERIE" ? "Hueco en la serie" : "Sin factura reciente") },
      { t: "Servicio", v: (r) => r.servicio },
      { t: "Medidor", v: (r) => r.medidor },
      { t: "Cadencia", v: (r) => r.cadencia },
      { t: "Entre", v: (r) => r.entre },
      { t: "Esperado", v: (r) => r.periodo_esperado },
      { t: "Detalle", v: (r) => r.detalle },
    ], lista, "Sin faltantes detectados."));
  }

  function facturas() {
    const lista = buscar(filtradas(false), $("buscar").value);
    const visibles = paginar(lista, "facturas", "pag-info", "ant", "sig");
    const caja = $("t-facturas");
    vaciar(caja);
    caja.appendChild(tabla([
      { t: "Sede", v: (r) => r.sede },
      { t: "Prestador", v: (r) => r.prestador },
      { t: "Servicio", v: (r) => r.servicio },
      { t: "Factura", v: (r) => r.factura },
      { t: "Periodo", v: (r) => r.periodo_fin },
      colConsumo,
      { t: "Valor", v: (r) => (r.valor === null ? "" : fmtMoneda.format(r.valor)), num: true },
      { t: "Estado", v: (r) => etiquetaEstado(r.estado) },
    ], visibles, "Sin facturas para los filtros y la búsqueda.", abrirDetalle));
  }

  function prestadores() {
    const por = {};
    filtradas(false).forEach((r) => {
      const p = (por[r.prestador] = por[r.prestador] || { n: 0, ok: 0, atip: 0, sinSerie: 0, baja: 0, conf: 0 });
      p.n += 1;
      if (r.estado === "OK") p.ok += 1;
      if (esAtipico(r)) p.atip += 1;
      if (r.estado === "SIN_SERIE") p.sinSerie += 1;
      if (r.estado === "REVISION_BAJA_CONFIANZA") p.baja += 1;
      p.conf += Number(r.confianza) || 0;
    });
    const lista = Object.entries(por).map(([prestador, p]) => ({ prestador, ...p }))
      .sort((a, b) => a.ok / a.n - b.ok / b.n);
    const caja = $("t-prestadores");
    vaciar(caja);
    caja.appendChild(tabla([
      { t: "Prestador", v: (r) => r.prestador },
      { t: "Facturas", v: (r) => fmt.format(r.n), num: true },
      { t: "Sin hallazgos", v: (r) => r.ok / r.n, tipo: "mini" },
      { t: "Atípicos", v: (r) => fmt.format(r.atip), num: true },
      { t: "Sin medidor", v: (r) => fmt.format(r.sinSerie), num: true },
      { t: "Baja confianza", v: (r) => fmt.format(r.baja), num: true },
      { t: "Confianza media", v: (r) => (r.conf / r.n).toFixed(2), num: true },
    ], lista, "Sin datos."));
  }

  // ---------- tabla generica ----------
  function tabla(columnas, filas, vacio, alClic) {
    if (!filas.length) return el("p", vacio || "Sin registros.", "vacio");
    const t = document.createElement("table");
    const cab = document.createElement("thead"), fc = document.createElement("tr");
    columnas.forEach((c) => fc.appendChild(el("th", c.t, c.num ? "num" : "")));
    cab.appendChild(fc);
    t.appendChild(cab);
    const cuerpo = document.createElement("tbody");
    filas.forEach((r) => {
      const tr = document.createElement("tr");
      if (alClic) {
        tr.className = "clic";
        tr.tabIndex = 0;
        tr.addEventListener("click", () => alClic(r));
        tr.addEventListener("keydown", (e) => { if (e.key === "Enter") alClic(r); });
      }
      columnas.forEach((c) => {
        const td = document.createElement("td");
        if (c.num) td.className = "num";
        const v = c.v(r);
        if (c.tipo === "sem") td.appendChild(el("span", v, "sem " + v));
        else if (c.tipo === "etq") td.appendChild(el("span", v, "etq " + (String(v).includes("alta") ? "ALTA" : String(v).includes("media") ? "MEDIA" : "")));
        else if (c.tipo === "mini") {
          const m = el("span", null, "mini"), b = el("span");
          b.style.width = `${Math.round(v * 100)}%`;
          m.appendChild(b);
          td.appendChild(m);
          td.appendChild(document.createTextNode(fmtPct(v)));
        } else td.textContent = v === null || v === undefined ? "" : String(v);
        tr.appendChild(td);
      });
      cuerpo.appendChild(tr);
    });
    t.appendChild(cuerpo);
    return t;
  }

  // ---------- detalle ----------
  function abrirDetalle(r) {
    const dl = $("detalle-lista");
    vaciar(dl);
    [["Factura", r.factura], ["Prestador", r.prestador], ["Servicio", r.servicio], ["Sede", r.sede],
      ["Dirección", r.direccion], ["Cuenta / medidor", r.cuenta], ["Periodo", `${r.periodo_inicio || "?"} → ${r.periodo_fin || "?"}`],
      ["Consumo", r.consumo === null ? "" : `${fmt.format(r.consumo)} ${r.unidad || ""}`],
      ["Valor", r.valor === null ? "" : fmtMoneda.format(r.valor)],
      ["Estado de validación", etiquetaEstado(r.estado)], ["Severidad", r.severidad], ["Detalle", r.detalle],
      ["Confianza", r.confianza], ["Revisión", r.revision], ["Archivo origen", r.archivo],
    ].forEach(([k, v]) => {
      dl.appendChild(el("dt", k));
      dl.appendChild(el("dd", v === null || v === undefined || v === "" ? "—" : v));
    });
    if (!$("detalle").open) $("detalle").showModal();
  }

  // ---------- CSV ----------
  function celdaCsv(v) {
    let s = v === null || v === undefined ? "" : String(v);
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;   // evita formulas en Excel (datos no confiables)
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }
  function descargar() {
    const filas = buscar(filtradas(false), $("buscar").value);
    const cols = ["sede", "prestador", "servicio", "factura", "cuenta", "periodo_inicio",
      "periodo_fin", "consumo", "unidad", "valor", "estado", "severidad", "detalle", "archivo"];
    const csv = [cols.join(",")].concat(filas.map((r) => cols.map((c) => celdaCsv(r[c])).join(","))).join("\r\n");
    const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "consumos_filtrados.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------- eventos ----------
  function cambiarVista(v) {
    vista = v;
    document.querySelectorAll(".segmento [data-vista]").forEach((b) =>
      b.setAttribute("aria-selected", String(b.dataset.vista === v)));
    $("vista-ejecutiva").hidden = v !== "ejecutiva";
    $("vista-operativa").hidden = v !== "operativa";
    renderizar();
  }
  function cambiarTab(t) {
    tab = t;
    document.querySelectorAll(".pestanas button").forEach((b) =>
      b.setAttribute("aria-selected", String(b.dataset.tab === t)));
    ["cola", "faltantes", "facturas", "prestadores"].forEach((x) => { $("tab-" + x).hidden = x !== t; });
    renderizar();
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("form-login").addEventListener("submit", ingresar);
    $("salir").addEventListener("click", salir);
    [["f-servicio", "servicio"], ["f-sede", "sede"], ["f-prestador", "prestador"],
      ["f-desde", "desde"], ["f-hasta", "hasta"]].forEach(([id, clave]) =>
      $(id).addEventListener("change", () => {
        F[clave] = $(id).value;
        // Rango coherente: si desde > hasta, se alinea el otro extremo.
        if (F.desde !== TODOS && F.hasta !== TODOS && F.desde > F.hasta) {
          if (clave === "desde") F.hasta = F.desde; else F.desde = F.hasta;
          sincronizarSelects();
        }
        pag.cola = 0; pag.facturas = 0;
        renderizar();
      }));
    $("limpiar").addEventListener("click", () => {
      Object.keys(F).forEach((k) => { F[k] = TODOS; });
      sincronizarSelects();
      renderizar();
    });
    document.querySelectorAll(".segmento [data-vista]").forEach((b) =>
      b.addEventListener("click", () => cambiarVista(b.dataset.vista)));
    document.querySelectorAll(".pestanas button").forEach((b) =>
      b.addEventListener("click", () => cambiarTab(b.dataset.tab)));
    document.querySelectorAll("#u-sede button").forEach((b) => b.addEventListener("click", () => {
      unidadSede = b.dataset.u;
      document.querySelectorAll("#u-sede button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      renderizar();
    }));
    $("f-hallazgo").addEventListener("change", () => { hallazgo = $("f-hallazgo").value; pag.cola = 0; renderizar(); });
    $("buscar-cola").addEventListener("input", () => { pag.cola = 0; renderizar(); });
    $("buscar").addEventListener("input", () => { pag.facturas = 0; renderizar(); });
    $("cola-ant").addEventListener("click", () => { pag.cola = Math.max(0, pag.cola - 1); renderizar(); });
    $("cola-sig").addEventListener("click", () => { pag.cola += 1; renderizar(); });
    $("ant").addEventListener("click", () => { pag.facturas = Math.max(0, pag.facturas - 1); renderizar(); });
    $("sig").addEventListener("click", () => { pag.facturas += 1; renderizar(); });
    $("descargar").addEventListener("click", descargar);
    $("cerrar-detalle").addEventListener("click", () => $("detalle").close());
    window.addEventListener("resize", () => Object.values(instancias).forEach((c) => c.resize()));
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderizar());
    $("correo").focus();
  });
})();
