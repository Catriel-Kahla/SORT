(() => {
  "use strict";

  let contribuyentes = [];
  let seleccionados = new Set();
  let ultimoResultado = null;

  const $ = (id) => document.getElementById(id);

  const pantallaCarga = $("pantallaCarga");
  const pantallaListado = $("pantallaListado");
  const pantallaResultado = $("pantallaResultado");
  const overlay = $("overlayCarga");
  const overlayTexto = $("overlayTexto");
  const mensajeError = $("mensajeError");
  const dropzone = $("dropzone");
  const cuerpoTabla = $("cuerpoTabla");
  const buscador = $("buscador");
  const checkTodos = $("checkTodos");
  const resumenSeleccion = $("resumenSeleccion");
  const contadorArchivo = $("contadorArchivo");
  const btnGenerar = $("btnGenerar");

  function mostrarPantalla(nombre) {
    pantallaCarga.classList.toggle("oculto", nombre !== "carga");
    pantallaListado.classList.toggle("oculto", nombre !== "listado");
    pantallaResultado.classList.toggle("oculto", nombre !== "resultado");
  }

  function mostrarOverlay(texto) {
    overlayTexto.textContent = texto || "Procesando...";
    overlay.classList.remove("oculto");
  }
  function ocultarOverlay() {
    overlay.classList.add("oculto");
  }

  function mostrarError(msg) {
    mensajeError.textContent = msg;
    mensajeError.classList.remove("oculto");
  }
  function limpiarError() {
    mensajeError.classList.add("oculto");
    mensajeError.textContent = "";
  }

  function formatearMoneda(v) {
    return v.toLocaleString("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 2 });
  }

  async function procesarResultadoCarga(resp) {
    if (!resp.ok) {
      if (!resp.cancelado) mostrarError(resp.error || "No se pudo leer el archivo.");
      return;
    }
    limpiarError();
    contribuyentes = resp.contribuyentes;
    seleccionados = new Set();
    contadorArchivo.textContent = resp.archivo.split(/[\\/]/).pop();
    contadorArchivo.classList.remove("chip-muted");
    prepararIndice(contribuyentes);
    buscador.value = "";
    orden = { clave: null, desc: true };
    actualizarEncabezados();
    aplicarVista();
    mostrarPantalla("listado");
  }

  async function elegirArchivo() {
    mostrarOverlay("Leyendo archivo...");
    try {
      const resp = await window.pywebview.api.elegir_archivo();
      await procesarResultadoCarga(resp);
    } finally {
      ocultarOverlay();
    }
  }

  const LOTE = 200;
  let vista = [];
  let renderizadas = 0;
  let orden = { clave: null, desc: true };
  const tablaWrap = document.querySelector(".tabla-wrap");

  const esc = (t) =>
    String(t ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const normalizar = (t) =>
    String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const soloDigitos = (t) => String(t || "").replace(/\D/g, "");

  const valorOrden = {
    cuit: (c) => c._cuitNum,
    nombre: (c) => c._nombreN,
    domicilio: (c) => normalizar(c.domicilio),
    cant_dominios: (c) => c.cant_dominios,
    deuda_total: (c) => c.deuda_total,
  };

  function prepararIndice(lista) {
    for (const c of lista) {
      c._cuitNum = soloDigitos(c.cuit);
      c._nombreN = normalizar(c.nombre);
      c._texto = c._nombreN + " " + normalizar(c.dominios.map((d) => d.dominio).join(" "));
    }
  }

  function htmlFila(c) {
    const sel = seleccionados.has(c.cuit);
    const dominiosTexto = c.dominios.map((d) => d.dominio).join(", ");
    return `<tr data-cuit="${esc(c.cuit)}"${sel ? ' class="seleccionada"' : ""}>
      <td class="col-check"><input type="checkbox" class="chk-fila"${sel ? " checked" : ""}></td>
      <td>${esc(c.cuit)}</td>
      <td>${esc(c.nombre)}<div class="fila-dominios">${esc(dominiosTexto)}</div></td>
      <td>${esc(c.domicilio || "-")}${c.localidad ? " · " + esc(c.localidad) : ""}</td>
      <td class="col-num">${c.cant_dominios}</td>
      <td class="col-num">${formatearMoneda(c.deuda_total)}</td>
    </tr>`;
  }

  function renderizarLote() {
    if (renderizadas >= vista.length) return;
    const fin = Math.min(renderizadas + LOTE, vista.length);
    let html = "";
    for (let i = renderizadas; i < fin; i++) html += htmlFila(vista[i]);
    cuerpoTabla.insertAdjacentHTML("beforeend", html);
    renderizadas = fin;
  }

  function renderizarTabla() {
    cuerpoTabla.innerHTML = "";
    renderizadas = 0;
    tablaWrap.scrollTop = 0;
    renderizarLote();
  }

  function aplicarVista() {
    const q = normalizar(buscador.value.trim());
    const qDig = soloDigitos(buscador.value);
    // Si el texto parece un CUIT (solo dígitos y guiones/espacios), se compara sin guiones
    const esCuit = qDig.length > 0 && /^[\d\s\-.]+$/.test(buscador.value.trim());
    vista = !q
      ? contribuyentes.slice()
      : contribuyentes.filter((c) =>
          esCuit ? c._cuitNum.includes(qDig) || c._texto.includes(q) : c._texto.includes(q) || (qDig.length >= 3 && c._cuitNum.includes(qDig))
        );
    if (orden.clave) {
      const f = valorOrden[orden.clave];
      const dir = orden.desc ? -1 : 1;
      vista.sort((a, b) => {
        const x = f(a), y = f(b);
        return x < y ? -dir : x > y ? dir : 0;
      });
    }
    renderizarTabla();
    actualizarResumen();
  }

  function actualizarEncabezados() {
    document.querySelectorAll("th[data-orden]").forEach((th) => {
      const activo = th.dataset.orden === orden.clave;
      th.classList.toggle("orden-activo", activo);
      th.dataset.dir = activo ? (orden.desc ? "desc" : "asc") : "";
    });
  }

  document.querySelectorAll("th[data-orden]").forEach((th) =>
    th.addEventListener("click", () => {
      const k = th.dataset.orden;
      // primer clic: mayor a menor; segundo: menor a mayor
      orden = orden.clave === k ? { clave: k, desc: !orden.desc } : { clave: k, desc: true };
      actualizarEncabezados();
      aplicarVista();
    })
  );

  tablaWrap.addEventListener("scroll", () => {
    if (tablaWrap.scrollTop + tablaWrap.clientHeight >= tablaWrap.scrollHeight - 300) renderizarLote();
  });

  cuerpoTabla.addEventListener("click", (ev) => {
    const tr = ev.target.closest("tr");
    if (!tr) return;
    const chk = tr.querySelector(".chk-fila");
    if (ev.target !== chk) chk.checked = !chk.checked;
    if (chk.checked) seleccionados.add(tr.dataset.cuit);
    else seleccionados.delete(tr.dataset.cuit);
    tr.classList.toggle("seleccionada", chk.checked);
    actualizarResumen();
  });

  function actualizarResumen() {
    resumenSeleccion.textContent = `${seleccionados.size} seleccionados` + (vista.length !== contribuyentes.length ? ` · ${vista.length} visibles` : "");
    btnGenerar.disabled = seleccionados.size === 0;
    checkTodos.checked = vista.length > 0 && vista.every((c) => seleccionados.has(c.cuit));
  }

  checkTodos.addEventListener("change", () => {
    for (const c of vista) {
      if (checkTodos.checked) seleccionados.add(c.cuit);
      else seleccionados.delete(c.cuit);
    }
    cuerpoTabla.querySelectorAll("tr").forEach((tr) => {
      const on = seleccionados.has(tr.dataset.cuit);
      tr.classList.toggle("seleccionada", on);
      tr.querySelector(".chk-fila").checked = on;
    });
    actualizarResumen();
  });

  let temporizador;
  buscador.addEventListener("input", () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(aplicarVista, 150);
  });


  $("btnElegirArchivo").addEventListener("click", elegirArchivo);
  $("btnCambiarArchivo").addEventListener("click", () => {
    limpiarError();
    mostrarPantalla("carga");
  });

  dropzone.addEventListener("click", (e) => {
    if (e.target.id !== "btnElegirArchivo") elegirArchivo();
  });
  ["dragenter", "dragover"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add("arrastrando");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove("arrastrando");
    })
  );
  dropzone.addEventListener("drop", async (e) => {
    const archivo = e.dataTransfer.files[0];
    if (!archivo || !archivo.path) {
      mostrarError("Arrastrá el archivo directamente desde el Explorador de Windows.");
      return;
    }
    mostrarOverlay("Leyendo archivo...");
    try {
      const resp = await window.pywebview.api.cargar_archivo(archivo.path);
      await procesarResultadoCarga(resp);
    } finally {
      ocultarOverlay();
    }
  });

  $("btnGenerar").addEventListener("click", async () => {
    if (seleccionados.size === 0) return;
    const convertirPdf = $("checkPdf").checked;
    mostrarOverlay(`Generando ${seleccionados.size} boleta(s)...`);
    try {
      const resp = await window.pywebview.api.generar(Array.from(seleccionados), convertirPdf);
      if (!resp.ok) {
        mostrarError(resp.error || "No se pudieron generar las boletas.");
        return;
      }
      ultimoResultado = resp;
      $("resultadoTitulo").textContent = `${resp.cantidad} boleta(s) generada(s)`;
      let detalle = `Se guardaron en: ${resp.carpeta}`;
      if (resp.error_pdf) {
        detalle += `\nNo se pudo convertir a PDF automáticamente (${resp.error_pdf}). Los .docx se generaron igual.`;
      }
      $("resultadoDetalle").textContent = detalle;
      mostrarPantalla("resultado");
    } finally {
      ocultarOverlay();
    }
  });

  $("btnAbrirCarpeta").addEventListener("click", () => {
    if (ultimoResultado) window.pywebview.api.abrir_carpeta(ultimoResultado.carpeta);
  });

  $("btnVolver").addEventListener("click", () => {
    mostrarPantalla("listado");
  });
})();
