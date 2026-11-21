"""Patch the stored dashboard page for the rework: state per finding, before/after tab."""

import json
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
t = json.load(open(SRC))["text"]


def rep(old: str, new: str) -> None:
    global t
    assert t.count(old) == 1, (t.count(old), old[:80])
    t = t.replace(old, new)


R = lambda name, field: f'<span data-draw="r-{name}" data-source="rework" data-field="{field}" data-row="0">—</span>'  # noqa: E731

# A. summary sentence
rep(
    '<b data-draw="k-f_high" data-source="kpi" data-field="f_high" data-row="0">—</b> Befunde der Stufe „hoch“ sind offen.',
    '<b data-draw="r-high" data-source="rework" data-field="high" data-row="0">—</b> Befunde der Stufe „hoch“ sind nach der Nachprüfung offen.',
)
# B. method paragraph
rep(
    "Die Aero-Stufe (echte Solver) wurde nur gelesen, nicht ausgeführt.</p>",
    "Die Aero-Stufe (echte Solver) wurde im Review nur gelesen. Am 21. November 2026 haben zwölf weitere Prüfer jeden Befund unabhängig nachgeprüft; "
    "Schwere und Stand der Befunde auf dieser Seite sind das Ergebnis dieser Nachprüfung.</p>",
)
# C. findings tile
rep(
    '<div class="kt-tile"><span class="kt-label">Befunde</span><span class="kt-big" data-draw="k-f_total" data-source="kpi" data-field="f_total" data-row="0">—</span><span class="kt-sub">hoch <span data-draw="k-f_high2" data-source="kpi" data-field="f_high" data-row="0">—</span> · mittel <span data-draw="k-f_medium" data-source="kpi" data-field="f_medium" data-row="0">—</span> · niedrig <span data-draw="k-f_low" data-source="kpi" data-field="f_low" data-row="0">—</span></span></div>',
    '<div class="kt-tile"><span class="kt-label">Befunde zu bearbeiten</span><span class="kt-big" data-draw="r-active" data-source="rework" data-field="active" data-row="0">—</span><span class="kt-sub">hoch '
    + R("high2", "high") + " · mittel " + R("medium", "medium") + " · niedrig " + R("low", "low") + " · im Review gemeldet: " + R("total", "total") + "</span></div>",
)
# D. tab
rep(
    '<button class="kt-tab" role="tab" data-tab="anforderungen" id="tab-anforderungen">Anforderungen</button>',
    '<button class="kt-tab" role="tab" data-tab="nachpruefung" id="tab-nachpruefung">Nachprüfung</button>\n    <button class="kt-tab" role="tab" data-tab="anforderungen" id="tab-anforderungen">Anforderungen</button>',
)
rep("const TABS = ['uebersicht', 'drilldown', 'befunde', 'anforderungen',", "const TABS = ['uebersicht', 'drilldown', 'befunde', 'nachpruefung', 'anforderungen',")

# E. new section
state_rows = [
    ("open", "offen", "bestätigt; wird im Arbeitspaket bearbeitet"),
    ("bundled", "gebündelt", "bestätigt, aber klein; wird mit einem anderen Befund derselben Testdatei erledigt"),
    ("waiting", "wartet auf Entscheidung", "sachlich bestätigt; der Test hängt an einer offenen Entscheidung des Maintainers"),
    ("dropped", "gestrichen", "zutreffend, aber ohne Risiko für Flugfähigkeit, Reichweite oder Nutzlast"),
    ("refuted", "widerlegt", "ein vorhandener Test fängt den Fehler bereits"),
    ("defect", "Produktionsfehler", "kein Testbefund: Fehler im Produktivcode, als Bug-Ticket oder Frage an den Maintainer geführt"),
]
sev_rows = [("high", "hoch"), ("medium", "mittel"), ("low", "niedrig")]
cell = lambda name, field: f'<td class="kt-r" data-draw="r-{name}" data-source="rework" data-field="{field}" data-row="0">—</td>'  # noqa: E731
section = (
    """  <section class="kt-sec" id="nachpruefung" data-page hidden>
    <h2 id="h-nachpruefung">Was die Nachprüfung geändert hat</h2>
    <p>Zwölf Prüfer, keiner davon der ursprüngliche Reviewer, haben jeden Befund am Code nachvollzogen. Bei Befunden der Stufen hoch und mittel wurde die Mutation erneut gesetzt oder neu geschrieben, niedrige Befunde wurden gelesen. Hoch bleibt ein Befund nur, wenn ein falscher Wert oder ein fehlender Fehler den Aufrufer erreicht und die Mutation überlebt.</p>
    <h3 id="h-np-stand">Stand der Befunde</h3>
    <div class="kt-scroll">
      <table class="kt-table" id="tabelle-np-stand">
        <thead><tr><th>Stand</th><th class="kt-r">Befunde</th><th>Bedeutung</th></tr></thead>
        <tbody>
"""
    + "".join(f"          <tr><td>{label}</td>{cell('s_' + key, key)}<td>{text}</td></tr>\n" for key, label, text in state_rows)
    + """        </tbody>
      </table>
    </div>
    <h3 id="h-np-schwere">Schwere vor und nach der Nachprüfung</h3>
    <p class="kt-muted">„Vorher“ zählt alle im Review gemeldeten Befunde, „nachher“ nur die offenen und gebündelten.</p>
    <div class="kt-scroll">
      <table class="kt-table" id="tabelle-np-schwere">
        <thead><tr><th>Schwere</th><th class="kt-r">vorher</th><th class="kt-r">nachher</th><th class="kt-r">hochgestuft auf diese Stufe</th><th class="kt-r">herabgestuft auf diese Stufe</th></tr></thead>
        <tbody>
"""
    + "".join(
        f"          <tr><td>{label}</td>{cell('b_' + key, 'b_' + key)}{cell('a_' + key, key)}{cell('up_' + key, 'up_' + key)}{cell('down_' + key, 'down_' + key)}</tr>\n"
        for key, label in sev_rows
    )
    + """        </tbody>
      </table>
    </div>
    <h3 id="h-np-pakete">Arbeitspakete nach der Nachprüfung</h3>
    <p class="kt-muted">Ein Klick auf eine Zeile öffnet die Befunde des Arbeitspakets.</p>
    <div class="kt-scroll">
      <table class="kt-table" id="tabelle-np-pakete" data-source="rework_wp" data-row-key="wp">
        <thead><tr><th data-field="wp">Arbeitspaket</th><th class="kt-r" data-field="wave">Welle</th><th class="kt-r" data-field="total">gemeldet</th><th class="kt-r" data-field="active">zu bearbeiten</th><th class="kt-r" data-field="high">hoch</th><th class="kt-r" data-field="medium">mittel</th><th class="kt-r" data-field="low">niedrig</th><th class="kt-r" data-field="waiting">wartet</th><th class="kt-r" data-field="dropped">gestrichen</th><th class="kt-r" data-field="refuted">widerlegt</th><th class="kt-r" data-field="defect">Produktionsfehler</th><th class="kt-r" data-field="fix_test">Testempfehlung korrigiert</th></tr></thead>
        <tbody data-draw="np-wp-body"></tbody>
      </table>
    </div>
    <h3 id="h-np-aero">Gegenprobe in der Aero-Stufe</h3>
    <p>Für überlebende Mutationen in Code, den Aero-Tests erreichen, liefen gezielt bis zu drei Aero-Tests. Schlägt einer fehl, besteht die Lücke nur in der schnellen Stufe, und der Befund ist höchstens mittel.</p>
    <div class="kt-scroll">
      <table class="kt-table" id="tabelle-np-aero" data-source="findings" data-row-key="id">
        <thead><tr><th data-field="id">ID</th><th data-field="severity">Schwere</th><th data-field="aero_outcome">Ergebnis der Aero-Tests</th><th data-field="aero_killed_by">gefangen von</th><th data-field="claim">Was unbemerkt falsch sein könnte</th></tr></thead>
        <tbody data-draw="np-aero-body"></tbody>
      </table>
    </div>
  </section>

  <section class="kt-sec" id="anforderungen" data-page hidden>"""
)
rep('  <section class="kt-sec" id="anforderungen" data-page hidden>', section)

# F. findings tab
rep(
    '<select class="dash-select" id="f-st" data-param="st" aria-label="Beleg"><option value="">Jeder Beleg</option><option value="MUTATION_SURVIVED">Mutation überlebt</option><option value="READ_ONLY">nur gelesen</option></select>',
    '<select class="dash-select" id="f-fst" data-param="fst" aria-label="Stand"><option value="">Jeder Stand</option><option value="active">zu bearbeiten (offen und gebündelt)</option><option value="open">offen</option><option value="bundled">gebündelt</option><option value="waiting_for_decision">wartet auf Entscheidung</option><option value="dropped">gestrichen</option><option value="refuted">widerlegt</option><option value="production_defect">Produktionsfehler</option></select>\n'
    '      <select class="dash-select" id="f-st" data-param="st" aria-label="Nachprüfung"><option value="">Jede Nachprüfung</option><option value="CONFIRMED">Mutation überlebt</option><option value="CONFIRMED_BY_READING">durch Lesen bestätigt</option><option value="REFUTED">widerlegt</option><option value="SEPARATE_DEFECT_TRACK">Produktionsfehler</option></select>',
)
rep('<h2 id="h-befunde">Befunde mit Beleg und empfohlenem Test</h2>', '<h2 id="h-befunde">Befunde mit Beleg, Nachprüfung und empfohlenem Test</h2>')
rep(
    '<thead><tr><th data-field="id">ID</th><th data-field="severity">Schwere</th><th data-field="category">Kategorie</th><th data-field="wp">Arbeitspaket</th>',
    '<thead><tr><th data-field="id">ID</th><th data-field="severity">Schwere</th><th data-field="state">Stand</th><th data-field="category">Kategorie</th><th data-field="wp">Arbeitspaket</th>',
)
rep(
    '<thead><tr><th data-field="id">ID</th><th data-field="severity">Schwere</th><th data-field="test">Test</th>',
    '<thead><tr><th data-field="id">ID</th><th data-field="severity">Schwere</th><th data-field="state">Stand</th><th data-field="test">Test</th>',
)
rep("const SEV = { high: ['hoch', 'bad'], medium: ['mittel', 'warn'], low: ['niedrig', ''] };",
    "const SEV = { high: ['hoch', 'bad'], medium: ['mittel', 'warn'], low: ['niedrig', ''], none: ['entfällt', ''] };\n"
    "  const STATE = { open: ['offen', ''], bundled: ['gebündelt', ''], waiting_for_decision: ['wartet auf Entscheidung', 'warn'], dropped: ['gestrichen', ''], refuted: ['widerlegt', 'ok'], production_defect: ['Produktionsfehler', 'bad'] };\n"
    "  const ACTIVE = (r) => r.state === 'open' || r.state === 'bundled';\n"
    "  const SEVL = ['high', 'medium', 'low'];")
rep("      if (c === 'severity') td(tr).appendChild(chip(SEV[r.severity][0], SEV[r.severity][1]));",
    "      if (c === 'severity') td(tr).appendChild(chip(SEV[r.severity][0], SEV[r.severity][1]));\n"
    "      else if (c === 'state') td(tr).appendChild(chip((STATE[r.state] || [r.state, ''])[0], (STATE[r.state] || ['', ''])[1]));")
for n in ("4", "4", "4"):
    pass
t = t.replace("message(tbody, 4,", "message(tbody, 5,")
rep("tbody.replaceChildren(...sel.map((r) => findingRow(r, ['id', 'severity', 'test', 'claim'])));", "tbody.replaceChildren(...sel.map((r) => findingRow(r, ['id', 'severity', 'state', 'test', 'claim'])));")
rep("    const order = { high: 0, medium: 1, low: 2 };\n    return rows.filter((r) => (!p.sev || r.severity === p.sev) && (!p.wp || r.wp === p.wp) && (!p.cat || r.category === p.cat) && (!p.st || r.status === p.st))",
    "    const order = { high: 0, medium: 1, low: 2, none: 3 };\n    const inState = (r) => !p.fst || (p.fst === 'active' ? ACTIVE(r) : r.state === p.fst);\n"
    "    return rows.filter((r) => (!p.sev || r.severity === p.sev) && (!p.wp || r.wp === p.wp) && (!p.cat || r.category === p.cat) && (!p.st || r.verdict === p.st) && inState(r))")
t = t.replace("message(tbody, 6, dash.data('findings')", "message(tbody, 7, dash.data('findings')")
rep("return message(tbody, 6, 'Kein Befund passt zu dieser Auswahl.');", "return message(tbody, 7, 'Kein Befund passt zu dieser Auswahl.');")
rep("findingRow(r, ['id', 'severity', 'category', 'wp', 'file', 'claim'])", "findingRow(r, ['id', 'severity', 'state', 'category', 'wp', 'file', 'claim'])")

# G. detail card
rep("    pair(dl, 'Befund', `${r.id} · ${SEV[r.severity][0]} · ${catName(r.category)} · ${r.wp}`);",
    "    pair(dl, 'Befund', `${r.id} · ${SEV[r.severity][0]} · ${catName(r.category)} · ${r.wp}`);\n"
    "    pair(dl, 'Stand', (STATE[r.state] || [r.state])[0] + (r.bundle_with ? ' mit ' + r.bundle_with : '') + (r.ticket ? ' · Ticket ' + r.ticket : '') + (r.maintainer_note ? ' · ' + r.maintainer_note : ''));\n"
    "    pair(dl, 'Schwere', SEV[r.severity][0] + (r.severity !== r.severity_review ? ' (im Review: ' + SEV[r.severity_review][0] + ')' : '') + (r.severity_reason ? ' · ' + r.severity_reason : ''));")
rep("    pair(dl, 'Art des Belegs', r.status === 'MUTATION_SURVIVED' ? 'Mutation überlebt (' + r.probe_id + ')' : r.status === 'READ_ONLY' ? 'durch Lesen, ohne Mutation' : 'unklar');\n    if (r.mutation) pair(dl, 'Abnahme-Mutation', r.mutation, 'kt-pre');\n    pair(dl, 'Empfohlener Test', r.recommended_test);",
    "    const VERDICT = { CONFIRMED: 'Mutation überlebt alle schnellen Tests', CONFIRMED_BY_READING: 'durch Lesen bestätigt, ohne Mutation', REFUTED: 'widerlegt', SEPARATE_DEFECT_TRACK: 'als Produktionsfehler nachgestellt' };\n"
    "    pair(dl, 'Nachprüfung', (VERDICT[r.verdict] || r.verdict) + (r.killed_by ? ' · gefangen von ' + r.killed_by : ''));\n"
    "    if (r.verifier_evidence) pair(dl, 'Beleg des Prüfers', r.verifier_evidence);\n"
    "    if (r.verifier_note) pair(dl, 'Hinweis des Prüfers', r.verifier_note);\n"
    "    if (r.mutation) pair(dl, 'Abnahme-Mutation', r.mutation + (r.patch_file ? '\\n' + r.patch_file : ''), 'kt-pre');\n"
    "    if (r.verdict === 'CONFIRMED') pair(dl, 'Aero-Stufe', AERO[r.aero_outcome] ? AERO[r.aero_outcome] + (r.aero_killed_by ? ': ' + r.aero_killed_by : '') : 'kein Aero-Test erreicht diesen Code');\n"
    "    pair(dl, 'Empfohlener Test', r.recommended_test);\n"
    "    if (r.recommended_test_ok !== 'yes' && r.recommended_test_note) pair(dl, 'Korrektur am Test', r.recommended_test_note);\n"
    "    if (r.hand_value_correction) pair(dl, 'Korrektur der Handwerte', r.hand_value_correction);")

# H. overview grid: open findings per review package
rep('<span>Anforderungen</span><span>Befunde</span><span>Mutationen überlebt</span>', '<span>Anforderungen</span><span>Befunde zu bearbeiten</span><span>Mutationen überlebt</span>')
rep('<div data-draw="pkg-grid" data-source="packages" id="paket-uebersicht"></div>', '<div data-draw="pkg-grid" data-source="packages findings" id="paket-uebersicht"></div>')
rep("    const out = rows.map((r) => {\n      const row = el('div', 'kt-grow');",
    "    const fnd = ok('findings') || [];\n    const act = (pkg, sev) => fnd.filter((f) => f.package === pkg && f.severity === sev && ACTIVE(f)).length;\n"
    "    const out = rows.map((r) => {\n      const row = el('div', 'kt-grow');\n      const fh = act(r.package, 'high'), fm = act(r.package, 'medium'), fl = act(r.package, 'low');")
rep("bar([{ label: 'hoch', value: r.findings_high, tone: 'bad' }, { label: 'mittel', value: r.findings_medium, tone: 'warn' }, { label: 'niedrig', value: r.findings_low }], r.findings_high + r.findings_medium + r.findings_low, host),",
    "bar([{ label: 'hoch', value: fh, tone: 'bad' }, { label: 'mittel', value: fm, tone: 'warn' }, { label: 'niedrig', value: fl }], fh + fm + fl, host),")

# calcs and drawings of the rework
rep("  const KPI = {",
    """  const AERO = { killed: 'ein Aero-Test schlägt fehl', survived: 'alle Aero-Tests bleiben grün', no_baseline: 'kein Aero-Test lief unverändert grün', timeout: 'Zeitlimit überschritten', patch_failed: 'Mutation nicht anwendbar' };
  dash.calc('rework', {
    title: 'Befunde nach der Nachprüfung',
    description: 'Zählt die Befunde nach Stand und Schwere, vor und nach der Nachprüfung vom 21.11.2026.',
    inputs: ['findings'],
    fn: (findings) => {
      const n = (test) => findings.filter(test).length;
      const active = findings.filter((f) => f.state === 'open' || f.state === 'bundled');
      const rank = { high: 0, medium: 1, low: 2 };
      const row = { total: findings.length, active: active.length,
        open: n((f) => f.state === 'open'), bundled: n((f) => f.state === 'bundled'), waiting: n((f) => f.state === 'waiting_for_decision'),
        dropped: n((f) => f.state === 'dropped'), refuted: n((f) => f.state === 'refuted'), defect: n((f) => f.state === 'production_defect') };
      ['high', 'medium', 'low'].forEach((s) => {
        row[s] = active.filter((f) => f.severity === s).length;
        row['b_' + s] = n((f) => f.severity_review === s);
        row['up_' + s] = active.filter((f) => f.severity === s && rank[f.severity_review] > rank[s]).length;
        row['down_' + s] = active.filter((f) => f.severity === s && rank[f.severity_review] < rank[s]).length;
      });
      return [row];
    },
  });
  dash.calc('rework_wp', {
    title: 'Arbeitspakete nach der Nachprüfung',
    description: 'Je Arbeitspaket: gemeldete Befunde, zu bearbeitende nach Schwere und die ausgeschiedenen nach Grund.',
    inputs: ['findings'],
    fn: (findings) => {
      const wave = { 'WP-P4a': 1, 'WP-P7b': 1, 'WP-P6a': 1, 'WP-P6b': 1, 'WP-P3': 1, 'WP-P1': 2, 'WP-P2': 2, 'WP-P5': 2, 'WP-P7a': 2, 'WP-P8a': 3, 'WP-P8b': 3, 'WP-P4b': 3 };
      return Object.keys(wave).map((wp) => {
        const all = findings.filter((f) => f.wp === wp); const active = all.filter((f) => f.state === 'open' || f.state === 'bundled');
        const n = (rows, test) => rows.filter(test).length;
        return { wp, wave: wave[wp], total: all.length, active: active.length,
          high: n(active, (f) => f.severity === 'high'), medium: n(active, (f) => f.severity === 'medium'), low: n(active, (f) => f.severity === 'low'),
          waiting: n(all, (f) => f.state === 'waiting_for_decision'), dropped: n(all, (f) => f.state === 'dropped'), refuted: n(all, (f) => f.state === 'refuted'),
          defect: n(all, (f) => f.state === 'production_defect'), fix_test: n(active, (f) => f.recommended_test_ok === 'no' || !!f.hand_value_correction) };
      });
    },
  });
  const RW = { 'r-high': 'high', 'r-high2': 'high', 'r-medium': 'medium', 'r-low': 'low', 'r-active': 'active', 'r-total': 'total',
    'r-s_open': 'open', 'r-s_bundled': 'bundled', 'r-s_waiting': 'waiting', 'r-s_dropped': 'dropped', 'r-s_refuted': 'refuted', 'r-s_defect': 'defect',
    'r-b_high': 'b_high', 'r-b_medium': 'b_medium', 'r-b_low': 'b_low', 'r-a_high': 'high', 'r-a_medium': 'medium', 'r-a_low': 'low',
    'r-up_high': 'up_high', 'r-up_medium': 'up_medium', 'r-up_low': 'up_low', 'r-down_high': 'down_high', 'r-down_medium': 'down_medium', 'r-down_low': 'down_low' };
  Object.entries(RW).forEach(([name, field]) => dash.draw(name, (node) => {
    const k = dash.data('rework');
    node.textContent = k.status === 'ok' && k.data && k.data[0] ? de(k.data[0][field]) : '—';
  }));

  const KPI = {""")
rep("  function filtered(id, tests) {",
    """  dash.draw('np-wp-body', (tbody) => {
    const k = dash.data('rework_wp');
    if (k.status !== 'ok' || !k.data) return message(tbody, 12, k.status === 'error' ? 'Die Befunde konnten nicht geladen werden.' : 'Lädt …');
    tbody.replaceChildren(...k.data.map((r) => {
      const tr = el('tr'); tr.dataset.key = encodeURIComponent(r.wp);
      td(tr, r.wp);
      ['wave', 'total', 'active', 'high', 'medium', 'low', 'waiting', 'dropped', 'refuted', 'defect', 'fix_test'].forEach((f) => td(tr, de(r[f]), 'kt-r'));
      clickable(tr, () => { dash.setParams({ wp: r.wp, sev: '', cat: '', st: '', fst: '' }); showTab('befunde', true); });
      return tr;
    }));
  });
  dash.draw('np-aero-body', (tbody) => {
    const rows = ok('findings');
    if (!rows) return message(tbody, 5, dash.data('findings').status === 'error' ? 'Die Befunde konnten nicht geladen werden.' : 'Lädt …');
    const sel = rows.filter((r) => r.aero_outcome);
    if (!sel.length) return message(tbody, 5, 'Für keinen Befund liegt ein Ergebnis der Aero-Stufe vor.');
    tbody.replaceChildren(...sel.map((r) => {
      const tr = el('tr'); tr.dataset.key = encodeURIComponent(r.id);
      td(tr, r.id); td(tr).appendChild(chip(SEV[r.severity][0], SEV[r.severity][1]));
      td(tr).appendChild(chip(AERO[r.aero_outcome] || r.aero_outcome, r.aero_outcome === 'killed' ? 'ok' : r.aero_outcome === 'survived' ? 'bad' : 'warn'));
      td(tr, r.aero_killed_by, 'kt-mono'); td(tr, short(r.claim, 220), 'kt-wide');
      clickable(tr, () => { dash.setParams({ fid: r.id }); showTab('befunde', true); });
      return tr;
    }));
  });

  function filtered(id, tests) {""")

assert "r.status ===" not in t.split("dash.draw('finding-detail'")[1].split("function filtered")[0]
json.dump({"text": t}, open(OUT, "w"), ensure_ascii=False)
open(OUT.replace(".json", ".html"), "w").write(t)
print(len(t))
