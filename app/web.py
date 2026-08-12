"""Pagina web local para usar TramIA."""

LANDING_PAGE = r'''<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TramIA | Orientacion de tramites</title>
  <style>
    :root { --ink:#12233c; --blue:#1967d2; --pale:#eef5ff; --line:#dbe5f0; --good:#0f8a5f; --warn:#b36500; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; background:#f6f9fc; color:var(--ink); }
    header { background:linear-gradient(120deg,#12345c,#1967d2); color:white; padding:30px max(24px,calc((100% - 1080px)/2)); }
    header h1 { margin:0; font-size:30px; } header p { margin:7px 0 0; opacity:.9; }
    main { max-width:1080px; margin:28px auto; padding:0 24px; display:grid; grid-template-columns:1.15fr .85fr; gap:22px; }
    section { background:white; border:1px solid var(--line); border-radius:16px; padding:24px; box-shadow:0 8px 24px #17355b0d; }
    h2 { margin:0 0 8px; font-size:20px; } .hint { color:#53657b; margin:0 0 20px; line-height:1.45; }
    label { display:block; margin:14px 0 6px; font-weight:650; font-size:14px; }
    input, textarea { width:100%; border:1px solid #bdcad9; border-radius:9px; padding:11px 12px; font:inherit; color:inherit; }
    textarea { min-height:105px; resize:vertical; } input:focus, textarea:focus { outline:3px solid #dcebff; border-color:var(--blue); }
    .docs { display:grid; gap:8px; margin-top:8px; } .doc { display:flex; gap:9px; align-items:center; padding:9px; border:1px solid var(--line); border-radius:9px; font-size:14px; }
    .doc input { width:auto; } button { background:var(--blue); color:white; border:0; padding:11px 16px; border-radius:9px; font-weight:700; font-size:14px; cursor:pointer; margin-top:20px; }
    button:hover { filter:brightness(.93); } button.secondary { margin-top:10px; background:#e8f0fb; color:#174d92; }
    #result { min-height:360px; } .empty { color:#6b7b90; padding:22px 0; } .status { display:inline-block; margin:10px 0; padding:6px 10px; border-radius:99px; font-size:12px; font-weight:800; background:#e7f6ef; color:var(--good); }
    .status.warn { background:#fff0da; color:var(--warn); } .box { margin-top:15px; border-top:1px solid var(--line); padding-top:14px; } ul { padding-left:20px; line-height:1.6; } a { color:var(--blue); } .trace { font-size:13px; color:#53657b; }
    .case { padding:10px 0; border-bottom:1px solid var(--line); font-size:14px; } .error { color:#a42929; background:#fff0f0; padding:12px; border-radius:9px; }
    @media (max-width:760px) { main { grid-template-columns:1fr; padding:0 14px; } header { padding:24px 18px; } }
  </style>
</head>
<body>
  <header><h1>TramIA</h1><p>Orientacion inicial de tramites con trazabilidad y supervision humana.</p></header>
  <main>
    <section>
      <h2>Inicia tu solicitud</h2>
      <p class="hint">Describe el tramite que necesitas. TramIA te indicara los requisitos conocidos y, si hace falta, lo derivara a un secretario.</p>
      <form id="request-form">
        <label for="name">Nombre completo</label><input id="name" required placeholder="Ej. Ana Perez">
        <label for="email">Correo electronico</label><input id="email" required type="email" placeholder="ana@correo.com">
        <label for="description">Que tramite necesitas?</label><textarea id="description" required placeholder="Ej. Necesito renovar mi cedula vencida"></textarea>
        <label>Documentos que ya tienes</label>
        <div class="docs">
          <label class="doc"><input type="checkbox" value="Cedula de identidad"> Cedula de identidad</label>
          <label class="doc"><input type="checkbox" value="Comprobante de pago"> Comprobante de pago</label>
          <label class="doc"><input type="checkbox" value="Correo electronico"> Correo electronico</label>
          <label class="doc"><input type="checkbox" value="Certificado de nacido vivo"> Certificado de nacido vivo</label>
        </div>
        <button type="submit">Analizar solicitud</button>
      </form>
    </section>
    <section id="result">
      <h2>Resultado de la orientacion</h2>
      <div id="result-content" class="empty">Completa el formulario para recibir una guia paso a paso.</div>
      <button id="pending" class="secondary" type="button">Ver casos para funcionario</button>
      <div id="pending-content"></div>
    </section>
  </main>
  <script>
    const escapeHtml = text => String(text).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
    const list = items => items.length ? `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : '<p>No hay elementos pendientes.</p>';
    document.querySelector('#request-form').addEventListener('submit', async event => {
      event.preventDefault();
      const content = document.querySelector('#result-content');
      content.className = 'empty'; content.textContent = 'Analizando la solicitud...';
      const documents = [...document.querySelectorAll('.doc input:checked')].map(item => ({name:item.value, valid:true}));
      const payload = {
        citizen_name: document.querySelector('#name').value,
        email: document.querySelector('#email').value,
        description: document.querySelector('#description').value,
        documents,
      };
      try {
        const response = await fetch('/api/solicitudes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
        const data = await response.json(); if (!response.ok) throw new Error(data.error || 'No se pudo procesar la solicitud.');
        const guide = data.guide, warning = data.human_review ? ' warn' : '';
        content.className = '';
        content.innerHTML = `<strong>${escapeHtml(guide.procedure_name || 'Solicitud por revisar')}</strong><br><span class="status${warning}">${escapeHtml(data.status.replaceAll('_',' '))}</span><p>${escapeHtml(guide.message)}</p>` +
          `<div class="box"><b>Documentos pendientes</b>${list(guide.missing_documents)}</div>` +
          `<div class="box"><b>Pasos sugeridos</b>${list(guide.steps)}</div>` +
          (guide.source_url ? `<div class="box"><a href="${guide.source_url}" target="_blank" rel="noreferrer">Consultar fuente oficial</a></div>` : '') +
          `<div class="box trace"><b>Codigo:</b> ${escapeHtml(data.code)}<br><b>Acciones registradas:</b> ${data.traceability.length}</div>`;
      } catch (error) { content.className = 'error'; content.textContent = error.message; }
    });
    document.querySelector('#pending').addEventListener('click', async () => {
      const output = document.querySelector('#pending-content'); output.textContent = 'Cargando...';
      const response = await fetch('/api/funcionarios/pendientes'); const cases = await response.json();
      output.innerHTML = cases.length ? cases.map(item => `<div class="case"><b>${escapeHtml(item.code)}</b><br>${escapeHtml(item.citizen_name)} - ${escapeHtml(item.description)}</div>`).join('') : '<p class="hint">No hay casos pendientes de revision.</p>';
    });
  </script>
</body>
</html>'''
