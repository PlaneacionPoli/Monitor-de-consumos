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
  let unidadMapa = "valor";
  let geoColombia = null;
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


  // ---------- iconos (lineales, un solo color: heredan currentColor) ----------
  const SVGNS = "http://www.w3.org/2000/svg";
  const ICONOS = {
    energia: "M13 2 4 14h6l-1 8 9-12h-6z",
    agua: "M12 3C8 9 6 12 6 15a6 6 0 0 0 12 0c0-3-2-6-6-12z",
    aseo: "M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3",
    valor: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM14.5 9.5C14 8.5 13 8 12 8c-1.4 0-2.5.8-2.5 2s1 1.7 2.5 2 2.5.8 2.5 2-1.1 2-2.5 2c-1 0-2-.5-2.5-1.5M12 6v2M12 16v2",
    revision: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8 12.5l2.8 2.8L16 9.5",
    alerta: "M12 3 2 20h20L12 3zM12 10v4M12 17v.5",
    edificio: "M4 21V5l8-2 8 2v16M9 21v-4h6v4M8 9h2M14 9h2M8 13h2M14 13h2",
    campus: "M3 10 12 5l9 5M5 10v8M9 10v8M15 10v8M19 10v8M3 20h18",
    enchufe: "M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0V8zM12 17v4",
    calendario: "M5 5h14v15H5zM5 10h14M9 3v4M15 3v4",
    buscar: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4",
    flecha: "M6 9l6 6 6-6",
    x: "M6 6l12 12M18 6 6 18",
    descarga: "M12 4v11M7 11l5 5 5-5M5 20h14",
    archivo: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
    escudo: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3zM9 12l2 2 4-4",
    hoja: "M5 19c0-8 5-13 14-14 0 9-5 14-14 14zM5 19c2-4 5-7 9-9",
    filtro: "M4 5h16l-6 8v6l-4-2v-4L4 5z",
    reloj: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
    gauge: "M4 18a9 9 0 1 1 16 0M12 18l4-6",
    lista: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
    salir: "M10 4H5v16h5M14 8l4 4-4 4M18 12H9",
    semaforo: "M8 3h8v18H8zM12 7h.01M12 12h.01M12 17h.01",
    todos: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    pin: "M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11zM12 7.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z",
    tendencia: "M4 17l5-5 4 4 7-8M15 8h5v5",
  };
  function icono(nombre) {
    const sv = document.createElementNS(SVGNS, "svg");
    sv.setAttribute("viewBox", "0 0 24 24");
    sv.setAttribute("class", "ico");
    sv.setAttribute("aria-hidden", "true");
    const p = document.createElementNS(SVGNS, "path");
    p.setAttribute("d", ICONOS[nombre] || ICONOS.archivo);
    sv.appendChild(p);
    return sv;
  }
  function hidratarIconos(raiz) {
    (raiz || document).querySelectorAll("[data-icono]").forEach((n) => {
      if (n.dataset.hecho) return;
      n.dataset.hecho = "1";
      n.insertBefore(icono(n.dataset.icono), n.firstChild);
    });
  }
  const etiquetaServicio = (v) => {
    const t = String(v || "");
    return t.toLowerCase() === "energia" ? "Energía" : t.charAt(0).toUpperCase() + t.slice(1);
  };
  const etiquetaUnidad = (u) => (u === "m3" ? "m³" : u || "");
  function iconoServicio(sv) {
    const t = String(sv || "").toLowerCase();
    if (t.includes("energ")) return "energia";
    if (t.includes("acued") || t.includes("agua")) return "agua";
    if (t.includes("aseo")) return "aseo";
    return "archivo";
  }

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

  // Modo local: si junto al tablero hay auto.json (solo lo genera `publicar_dashboard.py --local`), entra solo.
  async function autoIngreso() {
    try {
      const r = await fetch("auto.json", { cache: "no-store" });
      if (!r.ok) return;
      const a = await r.json();
      if (!a.correo || !a.contrasena) return;
      $("correo").value = a.correo;
      $("clave").value = a.contrasena;
      $("form-login").requestSubmit();
    } catch (e) { /* sitio publicado: no existe auto.json */ }
  }

  function salir() {
    Object.keys(instancias).forEach((id) => { instancias[id].dispose(); delete instancias[id]; });
    datos = null;
    $("app").hidden = true;
    $("login").hidden = false;
    $("correo").focus();
  }

  // ---------- filtros ----------
  const GRUPO_CSU = "CSU";               // los CSU se muestran como una sola sede desplegable
  const esCsu = (s) => /^CSU\b/.test(s || "");
  const etiquetaSede = (v) => (v === GRUPO_CSU ? "CSU · todos los centros" : v === "SIN_MAPEO" ? "Sin sede identificada" : v);
  const abierto = { rank: false, sem: false };   // CSU desplegado en ranking / semaforo
  const resetPag = () => { pag.cola = 0; pag.facturas = 0; };

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
      (F.sede === TODOS || r.sede === F.sede || (F.sede === GRUPO_CSU && esCsu(r.sede))) &&
      (F.prestador === TODOS || r.prestador === F.prestador) &&
      (F.estado === TODOS || r.estado === F.estado) &&
      (sinTiempo || ((F.desde === TODOS || (r.ymes && r.ymes >= F.desde)) &&
                     (F.hasta === TODOS || (r.ymes && r.ymes <= F.hasta))));
  }
  const filtradas = (sinTiempo) => datos.facturas.filter((r) => pasa(r, sinTiempo));

  // Conteo de facturas por valor de `campo` aplicando todos los filtros menos el de `clave`.
  function conteo(clave, campo) {
    const previo = F[clave];
    F[clave] = TODOS;
    const m = {};
    datos.facturas.forEach((r) => { if (pasa(r)) m[r[campo]] = (m[r[campo]] || 0) + 1; });
    F[clave] = previo;
    return m;
  }

  function sincronizarSelects() {
    $("f-desde").value = F.desde;
    $("f-hasta").value = F.hasta;
  }

  function fijar(clave, valor) {
    // Un segundo clic sobre el mismo valor lo quita (alternar).
    F[clave] = F[clave] === valor ? TODOS : valor;
    resetPag();
    renderizar();
  }

  function pildorasServicio() {
    const caja = $("f-servicio");
    vaciar(caja);
    const cnt = conteo("servicio", "servicio");
    [TODOS, ...unicos("servicio")].forEach((v) => {
      const b = el("button", null, "pildora");
      b.type = "button";
      b.setAttribute("aria-pressed", String(F.servicio === v));
      b.appendChild(icono(v === TODOS ? "todos" : iconoServicio(v)));
      b.appendChild(el("span", v === TODOS ? "Todos" : etiquetaServicio(v)));
      if (v !== TODOS) b.appendChild(el("small", fmt.format(cnt[v] || 0)));
      b.addEventListener("click", () => { F.servicio = v; resetPag(); renderizar(); });
      caja.appendChild(b);
    });
  }

  function pildorasRapidos() {
    const caja = $("f-rapidos");
    vaciar(caja);
    const meses = unicos("ymes");
    [["Todo", 0], ["3 meses", 3], ["6 meses", 6], ["12 meses", 12]].forEach(([t, n]) => {
      if (n && meses.length < n) return;
      const desde = n ? meses[meses.length - n] : TODOS;
      const b = el("button", t, "pildora chica");
      b.type = "button";
      b.setAttribute("aria-pressed", String(F.desde === desde && F.hasta === TODOS));
      b.addEventListener("click", () => { F.desde = desde; F.hasta = TODOS; resetPag(); renderizar(); });
      caja.appendChild(b);
    });
  }

  // ---- combo con busqueda (sede con CSU desplegable, prestador) ----
  const combos = {};
  function crearCombo(contId, cfg) {
    const caja = $(contId);
    let abiertoC = false, q = "";
    const grupos = new Set();
    const btn = el("button", null, "combo-btn");
    btn.type = "button";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    btn.appendChild(icono(cfg.icono));
    const txt = el("span", null, "combo-txt");
    txt.appendChild(el("small", cfg.titulo));
    const valor = el("strong");
    txt.appendChild(valor);
    btn.appendChild(txt);
    btn.appendChild(icono("flecha"));
    const panel = el("div", null, "combo-panel");
    panel.hidden = true;
    const buscador = el("label", null, "combo-buscar");
    buscador.appendChild(icono("buscar"));
    const entrada = el("input");
    entrada.type = "search";
    entrada.placeholder = `Buscar ${cfg.titulo.toLowerCase()}…`;
    entrada.setAttribute("aria-label", `Buscar ${cfg.titulo.toLowerCase()}`);
    buscador.appendChild(entrada);
    const lista = el("div", null, "combo-lista");
    lista.setAttribute("role", "listbox");
    panel.appendChild(buscador);
    panel.appendChild(lista);
    caja.appendChild(btn);
    caja.appendChild(panel);

    function opcion(o, hijo) {
      const b = el("button", null, "combo-op" + (hijo ? " hijo" : ""));
      b.type = "button";
      b.setAttribute("role", "option");
      b.setAttribute("aria-selected", String(F[cfg.clave] === o.v));
      if (o.icono) b.appendChild(icono(o.icono));
      b.appendChild(el("span", o.t, "op-t"));
      b.appendChild(el("small", fmt.format(o.n || 0)));
      if (!o.n && o.v !== TODOS) b.classList.add("sin");
      b.addEventListener("click", () => { F[cfg.clave] = o.v; resetPag(); cerrar(); renderizar(); });
      return b;
    }
    function dibujar() {
      vaciar(lista);
      const ql = q.trim().toLowerCase();
      const coincide = (o) => !ql || o.t.toLowerCase().includes(ql);
      lista.appendChild(opcion({ v: TODOS, t: cfg.todos, n: cfg.total() }));
      cfg.opciones().forEach((o) => {
        if (!o.hijos) { if (coincide(o)) lista.appendChild(opcion(o)); return; }
        const hijos = o.hijos.filter(coincide);
        if (!coincide(o) && !hijos.length) return;
        const fila = el("div", null, "combo-grupo");
        fila.appendChild(opcion(o));
        const ab = grupos.has(o.v) || !!ql;
        const t = el("button", null, "combo-chev" + (ab ? " abierto" : ""));
        t.type = "button";
        t.setAttribute("aria-label", ab ? "Plegar" : "Desplegar");
        t.setAttribute("aria-expanded", String(ab));
        t.appendChild(icono("flecha"));
        t.addEventListener("click", () => { if (grupos.has(o.v)) grupos.delete(o.v); else grupos.add(o.v); dibujar(); });
        fila.appendChild(t);
        lista.appendChild(fila);
        if (ab) (coincide(o) ? o.hijos : hijos).forEach((h) => lista.appendChild(opcion(h, true)));
      });
      if (lista.childNodes.length === 1) lista.appendChild(el("p", "Sin coincidencias.", "vacio"));
    }
    function abrir() {
      abiertoC = true; panel.hidden = false; btn.setAttribute("aria-expanded", "true");
      q = ""; entrada.value = ""; dibujar(); entrada.focus();
    }
    function cerrar() { abiertoC = false; panel.hidden = true; btn.setAttribute("aria-expanded", "false"); }
    btn.addEventListener("click", () => (abiertoC ? cerrar() : abrir()));
    entrada.addEventListener("input", () => { q = entrada.value; dibujar(); });
    caja.addEventListener("keydown", (e) => { if (e.key === "Escape") { cerrar(); btn.focus(); } });
    combos[contId] = {
      caja, cerrar,
      refrescar() {
        const v = F[cfg.clave];
        valor.textContent = v === TODOS ? cfg.todos : (cfg.etiqueta ? cfg.etiqueta(v) : v);
        btn.classList.toggle("activo", v !== TODOS);
        if (abiertoC) dibujar();
      },
    };
  }

  function crearCombos() {
    if (combos["c-sede"]) return;
    crearCombo("c-sede", {
      clave: "sede", titulo: "Sede", icono: "edificio", todos: "Todas las sedes", etiqueta: etiquetaSede,
      total: () => Object.values(conteo("sede", "sede")).reduce((a, b) => a + b, 0),
      opciones: () => {
        const cnt = conteo("sede", "sede");
        const todas = unicos("sede");
        const csu = todas.filter(esCsu).map((v) => ({ v, t: v, n: cnt[v] || 0, icono: "pin" }));
        const otras = todas.filter((s) => !esCsu(s)).map((v) => ({ v, t: etiquetaSede(v), n: cnt[v] || 0, icono: "edificio" }));
        const grupo = csu.length ? [{ v: GRUPO_CSU, t: `CSU · todos los centros (${csu.length})`, icono: "campus",
          n: csu.reduce((a, c) => a + c.n, 0), hijos: csu }] : [];
        return [...grupo, ...otras];
      },
    });
    crearCombo("c-prestador", {
      clave: "prestador", titulo: "Prestador", icono: "enchufe", todos: "Todos los prestadores",
      total: () => Object.values(conteo("prestador", "prestador")).reduce((a, b) => a + b, 0),
      opciones: () => {
        const cnt = conteo("prestador", "prestador");
        return unicos("prestador").map((v) => ({ v, t: v, n: cnt[v] || 0, icono: "enchufe" }));
      },
    });
  }

  function filtrosUI() {
    pildorasServicio();
    pildorasRapidos();
    sincronizarSelects();
    Object.values(combos).forEach((c) => c.refrescar());
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
      const valor = k === "estado" ? etiquetaEstado(F[k]) : k === "sede" ? etiquetaSede(F[k]) : k === "servicio" ? etiquetaServicio(F[k]) : F[k];
      c.appendChild(el("span", `${etiquetas[k]}: ${valor}`));
      const x = el("button", null, "chip-x");
      x.type = "button";
      x.setAttribute("aria-label", `Quitar filtro ${etiquetas[k]}`);
      x.appendChild(icono("x"));
      x.addEventListener("click", () => { F[k] = TODOS; resetPag(); renderizar(); });
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
    resetPag();
    abierto.rank = false; abierto.sem = false;
    const meses = unicos("ymes");
    llenar("f-desde", meses);
    llenar("f-hasta", meses);
    llenar("f-hallazgo", ["AUMENTO", "CAIDA", "ALTA", "MEDIA", "SIN_SERIE", "REVISION_BAJA_CONFIANZA",
      "REVISION_PERIODO_INFERIDO", "REVISION_UNIDAD"], (v) =>
      v === "AUMENTO" ? "Atípico · aumento" : v === "CAIDA" ? "Atípico · caída" : v === "ALTA" ? "Atípico · severidad alta" : v === "MEDIA" ? "Atípico · severidad media" : etiquetaEstado(v));
    crearCombos();
    renderizar();
  }

  // ---------- render ----------
  function renderizar() {
    if (!datos) return;
    chips();
    filtrosUI();
    if (vista === "ejecutiva") ejecutiva(); else operativa();
  }

  // ===== EJECUTIVA =====
  function ejecutiva() {
    const filas = filtradas(false);
    aviso();
    alertas(filas);
    kpisEjecutivos(filas);
    graficoMensual("g-energia", "kWh", css("--energia"));
    graficoMensual("g-agua", "m3", css("--agua"));
    graficoSedes(filas);
    graficoMapa(filas);
    calidad(filas);
    graficoValorMes(filas);
    graficoAtipicosMes(filas);
    graficoValorPor("g-prestador", filas, "prestador");
    graficoValorPor("g-valor-sede", filas, "sede");
    semaforo(filas);
  }

  // ---------- alertas de consumo atipico ----------
  function alertas(filas) {
    const caja = $("alertas");
    vaciar(caja);
    const atip = filas.filter(esAtipico);
    caja.hidden = !atip.length;
    if (!atip.length) return;
    const altas = atip.filter((r) => r.severidad === "ALTA");
    const cab = el("div", null, "cab-alertas");
    const h = el("h2", `${fmt.format(atip.length)} facturas con consumo atípico`, "con-icono");
    h.insertBefore(icono("alerta"), h.firstChild);
    cab.appendChild(h);
    const nAum = atip.filter((r) => r.sentido === "AUMENTO").length;
    const ver = el("button", "Ver todas en Operativa", "secundario chico-btn");
    ver.type = "button";
    ver.addEventListener("click", () => { hallazgo = altas.length ? "ALTA" : "MEDIA"; $("f-hallazgo").value = hallazgo; cambiarVista("operativa"); });
    cab.appendChild(ver);
    caja.appendChild(cab);
    caja.appendChild(el("p",
      `${fmt.format(nAum)} aumentos y ${fmt.format(atip.length - nAum)} caídas. ${fmt.format(altas.length)} de severidad alta (más de 50 % de variación) y ${fmt.format(atip.length - altas.length)} media (más de 20 %). ` +
      "Se compara el consumo por día contra la mediana robusta de la serie y de los pares del mes (la estacionalidad común no se marca). Los atípicos no entran en la referencia y en un cambio de nivel sostenido la alerta no se repite.",
      "suave pequeno"));
    const lista = document.createElement("ul");
    atip.slice().sort((a, b) => Math.abs(b.variacion || 0) - Math.abs(a.variacion || 0)).slice(0, 6).forEach((r) => {
      const li = document.createElement("li");
      const b = el("button");
      b.type = "button";
      b.appendChild(el("span", `${etiquetaSentido(r)} · ${r.severidad === "ALTA" ? "alta" : "media"}`, "etq " + (r.severidad || "")));
      b.appendChild(el("span", `${etiquetaSede(r.sede)} · ${etiquetaServicio(r.servicio)} · ${r.ymes || r.periodo_fin || ""}` +
        (r.bimestral ? " · bimestral" : "")));
      const v = Number(r.variacion);
      b.appendChild(el("span", Number.isFinite(v) ? `${v > 0 ? "+" : ""}${(v * 100).toFixed(0)} %` : "", "var " + (v > 0 ? "sube" : "baja")));
      b.addEventListener("click", () => abrirDetalle(r));
      li.appendChild(b);
      lista.appendChild(li);
    });
    caja.appendChild(lista);
  }

  // ---------- graficos de valor y atipicos ----------
  const COLOR_ASEO = "#8d6e63";
  const PARTES = [["energia", "Energía", () => css("--energia")], ["acueducto", "Acueducto", () => css("--agua")],
    ["aseo", "Aseo", () => COLOR_ASEO]];
  // Valor de una fila separado en componentes: servicio (energia/acueducto) y aseo.
  function componentes(r) {
    const aseo = Number(r.valor_aseo) || 0;
    const total = Number(r.valor) || 0;
    const servicio = r.valor_servicio !== null && r.valor_servicio !== undefined ? Number(r.valor_servicio) : total - aseo;
    return { [r.servicio]: servicio, aseo };
  }

  function apilado(id, categorias, series, opciones) {
    const nodo = $(id);
    if (!categorias.length) {
      if (instancias[id]) { instancias[id].dispose(); delete instancias[id]; }
      vaciar(nodo);
      nodo.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio"));
      return;
    }
    if (nodo.querySelector(".vacio")) vaciar(nodo);
    const chart = instancia(id);
    if (!chart) return;
    mesesDe[id] = opciones.meses ? categorias : undefined;
    const texto = css("--texto"), suave = css("--suave"), borde = css("--borde");
    const horizontal = !!opciones.horizontal;
    const eje = { type: "category", data: categorias, axisLabel: { color: suave, rotate: !horizontal && categorias.length > 8 ? 45 : 0 },
      axisLine: { lineStyle: { color: borde } }, axisTick: { show: false }, inverse: horizontal };
    const val = { type: "value", axisLabel: { color: suave, formatter: (v) => compacto.format(v) }, splitLine: { lineStyle: { color: borde } } };
    chart.setOption({
      animationDuration: 400, textStyle: { color: texto },
      color: series.map((x) => x.color),
      legend: { top: 0, textStyle: { color: suave }, itemWidth: 12, itemHeight: 8 },
      grid: { left: horizontal ? 120 : 52, right: 16, top: 30, bottom: horizontal ? 16 : 40 },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: css("--tarjeta"), borderColor: borde,
        textStyle: { color: texto }, valueFormatter: (v) => opciones.formato(v) },
      xAxis: horizontal ? val : eje, yAxis: horizontal ? eje : val,
      series: series.map((x) => ({ name: x.nombre, type: "bar", stack: "t", barMaxWidth: 34, cursor: opciones.meses ? "pointer" : "default",
        itemStyle: { color: x.color }, data: x.datos })),
    }, true);
    chart.resize();
  }

  function graficoValorMes(filas) {
    const por = {};
    filtradas(true).filter((r) => r.ymes).forEach((r) => {
      const m = (por[r.ymes] = por[r.ymes] || {});
      Object.entries(componentes(r)).forEach(([k, v]) => { m[k] = (m[k] || 0) + v; });
    });
    const meses = Object.keys(por).sort();
    apilado("g-valor", meses, PARTES.map(([k, nombre, color]) => ({ nombre, color: color(),
      datos: meses.map((m) => Math.round(por[m][k] || 0)) })), { meses: true, formato: (v) => fmtMoneda.format(v) });
  }

  function graficoAtipicosMes(filas) {
    const por = {};
    filtradas(true).filter((r) => r.ymes && esAtipico(r)).forEach((r) => {
      const m = (por[r.ymes] = por[r.ymes] || { AUMENTO: 0, CAIDA: 0 });
      m[r.sentido === "CAIDA" ? "CAIDA" : "AUMENTO"] += 1;
    });
    const meses = Object.keys(por).sort();
    apilado("g-atipicos", meses, [
      { nombre: "Aumentos", color: css("--alta"), datos: meses.map((m) => por[m].AUMENTO) },
      { nombre: "Caídas", color: css("--info"), datos: meses.map((m) => por[m].CAIDA) }],
      { meses: true, formato: (v) => fmt.format(v) });
  }

  function graficoValorPor(id, filas, campo) {
    const por = {};
    filas.forEach((r) => {
      const clave = campo === "sede" ? etiquetaSede(r[campo]) : r[campo] || "—";
      const m = (por[clave] = por[clave] || {});
      Object.entries(componentes(r)).forEach(([k, v]) => { m[k] = (m[k] || 0) + v; });
    });
    const total = (m) => Object.values(m).reduce((a, b) => a + b, 0);
    const nombres = Object.keys(por).sort((a, b) => total(por[b]) - total(por[a])).slice(0, 10);
    apilado(id, nombres, PARTES.map(([k, nombre, color]) => ({ nombre, color: color(),
      datos: nombres.map((n) => Math.round(por[n][k] || 0)) })), { horizontal: true, formato: (v) => fmtMoneda.format(v) });
  }

  function aviso() {
    const caja = $("aviso");
    const atip = datos.facturas.filter((r) => r.estado === "ATIPICO_REVISAR");
    const med3 = atip.filter((r) => (r.detalle || "").includes("serie corta")).length;
    if (atip.length && med3 / atip.length > 0.5) {
      caja.textContent =
        `${fmt.format(med3)} de ${fmt.format(atip.length)} atípicos están en series de menos de 6 periodos, ` +
        "con poca historia para estimar el comportamiento normal. Úselos para priorizar la revisión, no como diagnóstico.";
      caja.hidden = false;
    } else {
      caja.hidden = true;
    }
  }

  function kpiCaja(titulo, valor, sub, clase, unidad, ic) {
    const k = el("div", null, "kpi" + (clase ? " " + clase : ""));
    if (ic) { const c = el("span", null, "kpi-ico"); c.appendChild(icono(ic)); k.appendChild(c); }
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
    caja.appendChild(kpiCaja("Energía", fmt.format(sumar(filas.filter((r) => r.unidad === "kWh"), "consumo")), `${fmt.format(filas.filter((r) => r.unidad === "kWh").length)} facturas`, "k-energia", "kWh", "energia"));
    caja.appendChild(kpiCaja("Agua", fmt.format(sumar(filas.filter((r) => r.unidad === "m3"), "consumo")), `${fmt.format(filas.filter((r) => r.unidad === "m3").length)} facturas`, "k-agua", "m³", "agua"));
    caja.appendChild(kpiCaja("Valor facturado", fmtMoneda.format(sumar(filas, "valor")), `${fmt.format(total)} facturas`, "k-valor", "", "valor"));

    const auto = kpiCaja("Facturas sin revisión manual", fmtPct(pct),
      `Meta ${fmtPct(META_AUTOMATIZACION)} · mínimo ${fmtPct(MINIMO_AUTOMATIZACION)}`,
      pct < MINIMO_AUTOMATIZACION && total ? "alerta" : "k-ok", "", "revision");
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

    caja.appendChild(kpiCaja("Atípicos severidad alta", fmt.format(altas), "por revisar", altas ? "alerta" : "", "", "alerta"));
    caja.appendChild(kpiCaja("Posibles faltantes", fmt.format(falt), "facturas esperadas", falt ? "alerta" : "", "", "reloj"));
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
    const atipMes = {};
    filas.forEach((r) => { if (esAtipico(r)) atipMes[r.ymes] = (atipMes[r.ymes] || 0) + 1; });
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
          return `<b>${escapar(m)}</b><br>${fmt.format(por[m])} ${u}<br>${medidores[m].size} medidores con factura${parcial}` +
            (atipMes[m] ? `<br><b style="color:${css("--alta")}">${atipMes[m]} atípicos</b>` : "");
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
          itemStyle: { opacity: (enRango(m) ? 1 : 0.28) * (medidores[m].size / maxMed < 0.6 ? 0.6 : 1),
            borderColor: atipMes[m] ? css("--alta") : "transparent", borderWidth: atipMes[m] ? 2 : 0 },
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

  // Ranking de sedes en HTML: los CSU se muestran como una sola sede que se despliega.
  function filaRank(c) {
    const fila = el("button", null, "rank-fila" + (c.hijo ? " hijo" : ""));
    fila.type = "button";
    fila.setAttribute("aria-pressed", String(c.activo));
    fila.title = `${c.nombre}: ${fmt.format(c.valor)} ${c.unidad} (${fmtPct(c.valor / c.total)})`;
    fila.appendChild(el("span", c.hijo ? "" : c.indice, "rank-n"));
    const cuerpo = el("span", null, "rank-cuerpo");
    const nom = el("span", null, "rank-nombre");
    nom.appendChild(icono(c.ico));
    nom.appendChild(el("span", c.nombre));
    cuerpo.appendChild(nom);
    const pista = el("span", null, "rank-pista");
    const barra = el("span", null, c.unidad === "m³" ? "rank-barra agua" : "rank-barra");
    barra.style.width = `${Math.max(2, (c.valor / c.max) * 100)}%`;
    pista.appendChild(barra);
    cuerpo.appendChild(pista);
    fila.appendChild(cuerpo);
    const num = el("span", null, "rank-valor");
    num.appendChild(el("strong", fmt.format(c.valor)));
    num.appendChild(el("small", fmtPct(c.valor / c.total)));
    fila.appendChild(num);
    if (c.alClic) fila.addEventListener("click", c.alClic); else fila.disabled = true;
    return fila;
  }

  function graficoSedes(filas) {
    const unidad = unidadSede === "kWh" ? "kWh" : "m³";
    $("t-sede").lastChild.textContent = `Sedes con mayor consumo (${unidad})`;
    const por = {};
    filas.filter((r) => r.unidad === unidadSede).forEach((r) => {
      por[r.sede] = (por[r.sede] || 0) + (Number(r.consumo) || 0);
    });
    const entradas = [], hijos = [];
    let totalCsu = 0;
    Object.entries(por).forEach(([sede, valor]) => {
      if (esCsu(sede)) { totalCsu += valor; hijos.push({ sede, valor }); } else entradas.push({ sede, valor });
    });
    const desc = (a, b) => b.valor - a.valor;
    hijos.sort(desc);
    if (hijos.length) entradas.push({ sede: GRUPO_CSU, valor: totalCsu, hijos });
    entradas.sort(desc);
    const total = entradas.reduce((a, e) => a + e.valor, 0) || 1;
    const max = entradas.length ? entradas[0].valor : 1;
    const caja = $("g-sede");
    vaciar(caja);
    if (!entradas.length) { caja.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio")); return; }
    const lista = el("div", null, "ranking");
    entradas.slice(0, 12).forEach((e, i) => {
      const esGrupo = !!e.hijos;
      const sinMapeo = e.sede === "SIN_MAPEO";
      const fila = filaRank({
        indice: i + 1, nombre: esGrupo ? `CSU · ${e.hijos.length} centros` : etiquetaSede(e.sede), valor: e.valor,
        max, total, unidad, ico: esGrupo ? "campus" : "edificio", activo: F.sede === e.sede,
        alClic: sinMapeo ? null : () => fijar("sede", e.sede),
      });
      if (!esGrupo) { lista.appendChild(fila); return; }
      const grupo = el("div", null, "rank-grupo");
      const cab = el("div", null, "rank-cab");
      cab.appendChild(fila);
      const t = el("button", null, "chev" + (abierto.rank ? " abierto" : ""));
      t.type = "button";
      t.setAttribute("aria-expanded", String(abierto.rank));
      t.setAttribute("aria-label", abierto.rank ? "Plegar CSU" : "Desplegar CSU");
      t.appendChild(icono("flecha"));
      t.addEventListener("click", () => { abierto.rank = !abierto.rank; renderizar(); });
      cab.appendChild(t);
      grupo.appendChild(cab);
      if (abierto.rank) {
        const sub = el("div", null, "rank-hijos");
        const maxH = e.hijos[0].valor || 1;
        e.hijos.forEach((h) => sub.appendChild(filaRank({
          hijo: true, nombre: h.sede, valor: h.valor, max: maxH, total: e.valor || 1, unidad, ico: "pin",
          activo: F.sede === h.sede, alClic: () => fijar("sede", h.sede),
        })));
        grupo.appendChild(sub);
      }
      lista.appendChild(grupo);
    });
    caja.appendChild(lista);
  }


  // ---------- mapa de sedes (contorno DANE en colombia.geojson) ----------
  // [patron del nombre de sede (sin tildes, mayusculas), ciudad, longitud, latitud]; el orden importa.
  // Ubicacion por la direccion de cada sede (catalogo_sedes.csv), a nivel de calle; los CSU, por ciudad.
  const COORDS_SEDES = [
    [/CITY CAMPUS/, "Bogotá", -74.0620, 4.6475],   // Cl 61 # 7-69
    [/CALLE 84/, "Bogotá", -74.0545, 4.6700],      // Kr 19 # 84-72
    [/PORTAL 80/, "Bogotá", -74.1135, 4.7135],     // Tv 100A # 80A-20
    [/BOSA/, "Bogotá", -74.1900, 4.6100],          // Cl 65 # 78H Sur
    [/CAMPUS/, "Bogotá", -74.0636, 4.6410],        // Cl 57 # 3 Este-00 (sede principal)
    [/MEDELLIN|LOS COLORES/, "Medellín", -75.5950, 6.2620],
    [/CARTAGENA/, "Cartagena", -75.514, 10.391], [/BARRANQUILLA/, "Barranquilla", -74.796, 10.968],
    [/ZIPAQUIRA/, "Zipaquirá", -74.004, 5.022], [/CALI/, "Cali", -76.532, 3.452],
    [/CHIA/, "Chía", -74.0586, 4.8582], [/SOACHA/, "Soacha", -74.2168, 4.5791],
    [/VILLAVICENCIO/, "Villavicencio", -73.627, 4.142],
  ];
  const VISTAS_MAPA = { co: { center: null, zoom: 1 }, bog: { center: [-74.06, 4.66], zoom: 150 } };
  // Color por sede (estable por nombre); todos los CSU comparten un mismo color.
  const COLOR_CSU = "#E07B39";
  const PALETA_SEDES = ["#1B9AAA", "#6A4C93", "#2E7D32", "#C2185B", "#3F51B5", "#8D6E63", "#00897B", "#F9A825"];
  const esCSU = (sede) => /(^|[^A-Z])CSU[^A-Z]/.test(String(sede || "").toUpperCase() + " ");
  const colorSede = (sede, todas) => {
    if (esCSU(sede)) return COLOR_CSU;
    const propias = [...new Set(todas.filter((x) => !esCSU(x)))].sort();
    return PALETA_SEDES[propias.indexOf(sede) % PALETA_SEDES.length];
  };
  const coordenadaSede = (sede) => {
    const t = String(sede || "").toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return COORDS_SEDES.find((c) => c[0].test(t)) || null;
  };

  function cargarGeoColombia() {
    if (geoColombia) return Promise.resolve(geoColombia);
    return fetch("colombia.geojson").then((r) => r.json()).then((j) => {
      window.echarts.registerMap("CO", j);
      geoColombia = j;
      return j;
    });
  }

  // Diametro de la burbuja: crece con el valor y se achica al acercar para que sedes vecinas no se tapen.
  const diametroBurbuja = (rel, zoom) => Math.max(9, (14 + 40 * Math.sqrt(Math.max(rel, 0))) * (zoom >= 40 ? 0.4 : zoom >= 8 ? 0.65 : 1));

  function irAVista(clave) {
    const chart = instancias["g-mapa"];
    if (!chart) return;
    const v = VISTAS_MAPA[clave];
    chart.__vista = { center: v.center, zoom: v.zoom };
    chart.setOption({ geo: { center: v.center, zoom: v.zoom }, series: [{ symbolSize: chart.__tamano(v.zoom) }] });
  }

  function graficoMapa(filas) {
    const medida = unidadMapa;
    const rotulo = medida === "valor" ? "Valor facturado ($)" : medida === "kWh" ? "Consumo de energía (kWh)" : "Consumo de agua (m³)";
    $("t-mapa").lastChild.textContent = ` Mapa de sedes · ${rotulo}`;
    const por = {};
    filas.forEach((r) => {
      if (medida !== "valor" && r.unidad !== medida) return;
      const v = medida === "valor" ? Number(r.valor) || 0 : Number(r.consumo) || 0;
      por[r.sede] = (por[r.sede] || 0) + v;
    });
    const puntos = [];
    let sinUbicar = 0;
    Object.entries(por).forEach(([sede, valor]) => {
      const c = coordenadaSede(sede);
      if (!c) { if (valor > 0) sinUbicar += 1; return; }
      puntos.push({ sede, valor, ciudad: c[1], lon: c[2], lat: c[3] });
    });
    const nombresSedes = puntos.map((p) => p.sede);
    puntos.forEach((p) => { p.color = colorSede(p.sede, nombresSedes); });
    puntos.sort((a, b) => b.valor - a.valor);   // las grandes se dibujan primero; las pequenas quedan encima
    const nota = $("p-mapa");
    nota.textContent = (puntos.length
      ? "Rueda del ratón o arrastre para acercar y mover; use «Bogotá» para separar Campus, City Campus y Calle 84. Clic en una burbuja filtra por esa sede."
      : "Sin datos para los filtros elegidos.") +
      (sinUbicar ? ` ${sinUbicar} sede(s) sin ubicación en el mapa.` : "");
    let ley = $("l-mapa");
    if (!ley) {
      ley = document.createElement("div");
      ley.id = "l-mapa"; ley.className = "leyenda-mapa";
      nota.parentNode.insertBefore(ley, nota);
    }
    const entradas = [...new Map(puntos.map((p) => [esCSU(p.sede) ? "CSU (todos)" : etiquetaSede(p.sede), p.color])).entries()];
    ley.innerHTML = entradas.map(([n, c]) => `<span><i style="background:${c}"></i>${n}</span>`).join("");
    const chart = instancia("g-mapa");
    if (!chart) return;
    const max = Math.max(...puntos.map((p) => p.valor), 1);
    const color = medida === "valor" ? css("--acento") : medida === "kWh" ? css("--energia") : css("--agua");
    const formato = (v) => (medida === "valor" ? fmtMoneda.format(v) : `${fmt.format(v)} ${medida === "kWh" ? "kWh" : "m³"}`);
    const vista = chart.__vista || VISTAS_MAPA.co;
    cargarGeoColombia().then(() => {
      chart.setOption({
        tooltip: {
          trigger: "item",
          formatter: (p) => (p.data && p.data.sede
            ? `<b>${etiquetaSede(p.data.sede)}</b><br>${p.data.ciudad} · ${formato(p.data.value[2])}` : ""),
        },
        geo: {
          map: "CO", roam: true, scaleLimit: { min: 1, max: 400 },
          boundingCoords: [[-79.4, 13.2], [-66.6, -4.4]], layoutCenter: ["50%", "50%"], layoutSize: "112%", aspectScale: 1,
          center: vista.center || undefined, zoom: vista.zoom,
          itemStyle: { areaColor: "#E3F3FA", borderColor: "#9FCBE0", borderWidth: 0.6 },
          emphasis: { itemStyle: { areaColor: "#D2ECF7" }, label: { show: false } },
          select: { disabled: true },
        },
        series: [{
          type: "scatter", coordinateSystem: "geo",
          data: puntos.map((p) => ({ sede: p.sede, ciudad: p.ciudad, value: [p.lon, p.lat, p.valor], itemStyle: { color: p.color } })),
          symbolSize: (v) => diametroBurbuja(v[2] / max, vista.zoom),
          itemStyle: { color, opacity: 0.8, borderColor: "#fff", borderWidth: 1.5 },
          label: {
            show: true, position: "right", distance: 6, color: "#263A58", fontSize: 11, fontWeight: 600,
            formatter: (p) => etiquetaSede(p.data.sede).replace(/^(BOGOTA|MEDELLIN)-/, ""),
            textBorderColor: "#fff", textBorderWidth: 3,
          },
          labelLayout: { hideOverlap: true },
          emphasis: { scale: 1.15, itemStyle: { opacity: 1 } },
        }],
      }, true);
      chart.__tamano = (zoom) => (v) => diametroBurbuja(v[2] / max, zoom);
      if (!chart.__eventosMapa) {
        chart.__eventosMapa = true;
        chart.on("click", (p) => { if (p.data && p.data.sede) fijar("sede", p.data.sede); });
        chart.on("georoam", () => {    // recuerda el encuadre para no perderlo al filtrar
          const g = chart.getOption().geo[0];
          chart.__vista = { center: g.center, zoom: g.zoom };
          chart.setOption({ series: [{ symbolSize: chart.__tamano(g.zoom) }] });
        });
      }
      chart.resize();
    }).catch(() => { nota.textContent = "No se pudo cargar el contorno del mapa."; });
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

  // Semaforo por sede: una tarjeta por sede (los CSU, juntos y desplegables), ordenadas por criticidad.
  function semaforo(filas) {
    const nueva = () => ({ n: 0, ok: 0, atip: 0, alta: 0, kwh: 0, m3: 0 });
    const sumarEn = (s, r) => {
      s.n += 1;
      if (r.estado === "OK") s.ok += 1;
      if (r.estado === "ATIPICO_REVISAR") { s.atip += 1; if (r.severidad === "ALTA") s.alta += 1; }
      if (r.unidad === "kWh") s.kwh += Number(r.consumo) || 0;
      if (r.unidad === "m3") s.m3 += Number(r.consumo) || 0;
    };
    const por = {}, csu = nueva();
    filas.forEach((r) => {
      sumarEn((por[r.sede] = por[r.sede] || nueva()), r);
      if (esCsu(r.sede)) sumarEn(csu, r);
    });
    const rango = { Crítico: 0, Atención: 1, Normal: 2 };
    const nivel = (s) => (s.alta >= 3 ? "Crítico" : (s.atip > 0 || s.ok / s.n < 0.6 ? "Atención" : "Normal"));
    const ordenar = (a, b) => rango[a.nivel] - rango[b.nivel] || b.alta - a.alta || b.n - a.n;
    const centros = Object.entries(por).filter(([sede]) => esCsu(sede))
      .map(([sede, s]) => ({ sede, ...s, nivel: nivel(s) })).sort(ordenar);
    const lista = Object.entries(por).filter(([sede]) => !esCsu(sede))
      .map(([sede, s]) => ({ sede, ...s, nivel: nivel(s) }));
    if (centros.length) lista.push({ sede: GRUPO_CSU, ...csu, nivel: nivel(csu), hijos: centros });
    lista.sort(ordenar);
    const caja = $("t-semaforo");
    vaciar(caja);
    if (!lista.length) { caja.appendChild(el("p", "Sin datos para los filtros elegidos.", "vacio")); return; }

    function tarjeta(r, ico, nombre, ancha) {
      const t = el("button", null, "tile " + r.nivel + (ancha ? " ancha" : ""));
      t.type = "button";
      t.setAttribute("aria-pressed", String(F.sede === r.sede));
      t.appendChild(el("span", r.nivel, "sem " + r.nivel));
      const nom = el("span", null, "tile-nombre");
      nom.appendChild(icono(ico));
      nom.appendChild(el("span", nombre));
      t.appendChild(nom);
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
      return t;
    }

    const rejilla = el("div", null, "tiles");
    lista.forEach((r) => {
      if (!r.hijos) {
        rejilla.appendChild(tarjeta(r, "edificio", etiquetaSede(r.sede)));
        return;
      }
      const envoltura = el("div", null, "tile-wrap" + (abierto.sem ? " abierto" : ""));
      envoltura.appendChild(tarjeta(r, "campus", `CSU · ${r.hijos.length} centros`, abierto.sem));
      const t = el("button", null, "chev tile-chev" + (abierto.sem ? " abierto" : ""));
      t.type = "button";
      t.setAttribute("aria-expanded", String(abierto.sem));
      t.setAttribute("aria-label", abierto.sem ? "Plegar CSU" : "Desplegar CSU");
      t.appendChild(icono("flecha"));
      t.addEventListener("click", () => { abierto.sem = !abierto.sem; renderizar(); });
      envoltura.appendChild(t);
      if (abierto.sem) {
        const sub = el("div", null, "tiles hijos");
        r.hijos.forEach((h) => sub.appendChild(tarjeta(h, "pin", h.sede)));
        envoltura.appendChild(sub);
      }
      rejilla.appendChild(envoltura);
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
  const etiquetaSentido = (r) => (r.sentido === "CAIDA" ? "Caída" : r.sentido === "AUMENTO" ? "Aumento" : "Atípico");
  function coincideHallazgo(r) {
    if (hallazgo === TODOS) return r.estado !== "OK";
    if (hallazgo === "ALTA" || hallazgo === "MEDIA") return esAtipico(r) && r.severidad === hallazgo;
    if (hallazgo === "AUMENTO" || hallazgo === "CAIDA") return esAtipico(r) && r.sentido === hallazgo;
    return r.estado === hallazgo;
  }

  function resumenCola() {
    const filas = filtradas(false);
    const caja = $("cola-resumen");
    vaciar(caja);
    const items = [
      [TODOS, "Por revisar", filas.filter((r) => r.estado !== "OK").length],
      ["AUMENTO", "Aumentos", filas.filter((r) => esAtipico(r) && r.sentido === "AUMENTO").length],
      ["CAIDA", "Caídas", filas.filter((r) => esAtipico(r) && r.sentido === "CAIDA").length],
      ["ALTA", "Atípicos · alta", filas.filter((r) => esAtipico(r) && r.severidad === "ALTA").length],
      ["MEDIA", "Atípicos · media", filas.filter((r) => esAtipico(r) && r.severidad === "MEDIA").length],
      ["SIN_SERIE", "Sin medidor", filas.filter((r) => r.estado === "SIN_SERIE").length],
      ["REVISION_BAJA_CONFIANZA", "Baja confianza", filas.filter((r) => r.estado === "REVISION_BAJA_CONFIANZA").length],
    ];
    items.forEach(([clave, titulo, n]) => {
      const b = el("button", null, "kpi clic");
      b.type = "button";
      b.setAttribute("aria-pressed", String(hallazgo === clave));
      const ic = el("span", null, "kpi-ico");
      ic.appendChild(icono({ AUMENTO: "tendencia", CAIDA: "tendencia", ALTA: "alerta", MEDIA: "alerta", SIN_SERIE: "gauge", REVISION_BAJA_CONFIANZA: "escudo" }[clave] || "revision"));
      b.appendChild(ic);
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
    const icF = el("span", null, "kpi-ico");
    icF.appendChild(icono("reloj"));
    f.appendChild(icF);
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
      { t: "Hallazgo", v: (r) => (esAtipico(r) ? `${etiquetaSentido(r)} ${(r.severidad || "").toLowerCase()}` : etiquetaEstado(r.estado)), tipo: "etq" },
      { t: "Sede", v: (r) => r.sede },
      { t: "Servicio", v: (r) => r.servicio },
      { t: "Periodo", v: (r) => r.periodo_fin },
      { t: "Factura", v: (r) => r.factura },
      { t: "Cuenta", v: (r) => r.cuenta },
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
      { t: "Cuenta", v: (r) => r.cuenta },
      { t: "Periodo", v: (r) => r.periodo_fin + (r.bimestral ? " (bim.)" : "") },
      colConsumo,
      { t: "Valor", v: (r) => (r.valor === null ? "" : fmtMoneda.format(r.valor)), num: true },
      { t: "Aseo", v: (r) => (Number(r.valor_aseo) > 0 ? fmtMoneda.format(r.valor_aseo) : ""), num: true },
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

  // ---------- ficha de la factura ----------
  function abrirDetalle(r) {
    const est = ESTADOS[r.estado];
    const ico = $("ficha-icono");
    vaciar(ico);
    ico.appendChild(icono(iconoServicio(r.servicio)));
    $("detalle-titulo").textContent = !r.factura || /no identificado/i.test(r.factura) ? "Factura sin número identificado" : `Factura ${r.factura}`;
    $("ficha-sub").textContent = [r.prestador, etiquetaServicio(r.servicio), etiquetaSede(r.sede)].filter(Boolean).join(" · ");
    const insignia = $("ficha-estado");
    insignia.textContent = esAtipico(r) && r.severidad ? `${etiquetaSentido(r)} · ${String(r.severidad).toLowerCase()}` : etiquetaEstado(r.estado);
    insignia.style.setProperty("--c", css(est ? est[1] : "--neutro"));

    const cuerpo = $("ficha-cuerpo");
    vaciar(cuerpo);
    const vacioTxt = (v) => (v === null || v === undefined || v === "" ? "—" : v);
    const stats = el("div", null, "ficha-stats");
    [[`Consumo`, r.consumo === null ? "—" : `${fmt.format(r.consumo)} ${etiquetaUnidad(r.unidad)}`, iconoServicio(r.servicio)],
      ["Valor facturado", r.valor === null ? "—" : fmtMoneda.format(r.valor), "valor"],
      ...(Number(r.valor_aseo) > 0 ? [["Del cual aseo", fmtMoneda.format(r.valor_aseo), "aseo"]] : []),
      ["Periodo", `${r.periodo_inicio || "?"} → ${r.periodo_fin || "?"}`, "calendario"]].forEach(([t, v, ic]) => {
      const c = el("div", null, "ficha-stat");
      const i = el("span", null, "kpi-ico");
      i.appendChild(icono(ic));
      c.appendChild(i);
      c.appendChild(el("small", t));
      c.appendChild(el("strong", v));
      stats.appendChild(c);
    });
    cuerpo.appendChild(stats);

    const conf = Number(r.confianza);
    if (!Number.isNaN(conf) && r.confianza !== null && r.confianza !== "") {
      const caja = el("div", null, "ficha-conf");
      const cab = el("div", null, "ficha-conf-cab");
      cab.appendChild(el("span", "Confianza de la extracción"));
      cab.appendChild(el("strong", fmtPct(conf)));
      caja.appendChild(cab);
      const m = el("span", null, "mini ancho"), b = el("span");
      b.style.width = `${Math.max(0, Math.min(100, conf * 100))}%`;
      m.appendChild(b);
      caja.appendChild(m);
      cuerpo.appendChild(caja);
    }

    function seccion(titulo, ic, pares) {
      const sec = el("section", null, "ficha-sec");
      const h = el("h3", titulo);
      h.insertBefore(icono(ic), h.firstChild);
      sec.appendChild(h);
      const dl = el("dl");
      pares.forEach(([k, v]) => { dl.appendChild(el("dt", k)); dl.appendChild(el("dd", vacioTxt(v))); });
      sec.appendChild(dl);
      cuerpo.appendChild(sec);
    }
    seccion("Identificación", "archivo", [["Factura", r.factura], ["Prestador", r.prestador], ["Servicio", etiquetaServicio(r.servicio)],
      ["Sede", etiquetaSede(r.sede)], ["Dirección", r.direccion], ["Cuenta / contrato", r.cuenta],
      ["Periodicidad", r.bimestral ? `Bimestral (${r.dias || "?"} días)` : "Mensual"]]);
    seccion("Validación", "escudo", [["Estado", etiquetaEstado(r.estado)], ["Sentido", esAtipico(r) ? etiquetaSentido(r) : null], ["Severidad", r.severidad],
      ["Detalle", r.detalle], ["Consumo de referencia", r.consumo_ref === null || r.consumo_ref === undefined ? null : `${fmt.format(r.consumo_ref)} ${etiquetaUnidad(r.unidad)} esperados (${r.metodo_ref})`],
      ["Revisión", r.revision]]);

    const pie = $("ficha-archivo");
    vaciar(pie);
    pie.appendChild(icono("archivo"));
    pie.appendChild(document.createTextNode(` Archivo origen: ${vacioTxt(r.archivo)}`));
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
      "periodo_fin", "bimestral", "consumo", "unidad", "valor", "valor_servicio", "valor_aseo", "estado", "sentido", "severidad", "detalle", "archivo"];
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
    autoIngreso();
    $("salir").addEventListener("click", salir);
    [["f-desde", "desde"], ["f-hasta", "hasta"]].forEach(([id, clave]) =>
      $(id).addEventListener("change", () => {
        F[clave] = $(id).value;
        // Rango coherente: si desde > hasta, se alinea el otro extremo.
        if (F.desde !== TODOS && F.hasta !== TODOS && F.desde > F.hasta) {
          if (clave === "desde") F.hasta = F.desde; else F.desde = F.hasta;
        }
        resetPag();
        renderizar();
      }));
    $("limpiar").addEventListener("click", () => {
      Object.keys(F).forEach((k) => { F[k] = TODOS; });
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
    document.querySelectorAll("#z-mapa button").forEach((b) => b.addEventListener("click", () => irAVista(b.dataset.z)));
    document.querySelectorAll("#u-mapa button").forEach((b) => b.addEventListener("click", () => {
      unidadMapa = b.dataset.u;
      document.querySelectorAll("#u-mapa button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
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
    document.addEventListener("click", (e) => Object.values(combos).forEach((c) => { if (!c.caja.contains(e.target)) c.cerrar(); }));
    $("detalle").addEventListener("click", (e) => { if (e.target === $("detalle")) $("detalle").close(); });
    hidratarIconos();
    $("correo").focus();
  });
})();
