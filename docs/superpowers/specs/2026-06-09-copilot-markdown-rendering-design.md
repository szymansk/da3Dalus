# Design: Markdown + LaTeX Rendering im Copilot-Chat

**Datum:** 2026-06-09
**Scope:** Frontend-only
**Status:** Spec — wartet auf Review

## Problem

Das Copilot-Chat-Fenster (`frontend/components/workbench/CopilotStrip.tsx`)
rendert Assistant-Antworten aktuell als **reinen Text** (`{content}` mit
`whitespace-pre-wrap`). Der Copilot gibt jedoch Markdown (Überschriften,
Listen, Code, Tabellen) und LaTeX-Formeln aus. Dadurch ist die Ausgabe
schwer lesbar: Markdown-Syntax und rohe `$...$`-Formeln erscheinen als
literaler Text.

## Ziel

Assistant-Bubbles rendern **volles GitHub-Flavored Markdown plus
LaTeX-Formeln** (KaTeX), auch **live während des Token-Streamings**.
User-Bubbles bleiben Klartext.

## Entscheidungen (mit User abgestimmt)

| Frage | Entscheidung |
|---|---|
| Render-Umfang | Volles Markdown (GFM) **+** LaTeX (inline `$...$`, Block `$$...$$`) |
| Welche Bubbles | **Nur Assistant.** User-Eingaben bleiben Klartext |
| Streaming | **Live rendern** — Markdown/LaTeX schon während des Streamings |
| Library | **`streamdown`** (Vercel) — für AI-Token-Streaming gebaut |
| Code-Highlighting | **Shiki an** (streamdown-Default) |
| Ticketing | Spec → GH-Feature-Issue → `/supercycle-implement` |

## Warum streamdown

`streamdown` ist Vercels Markdown-Renderer speziell für **streamende
LLM-Tokens**. Er behandelt unvollständige/ungeschlossene Blöcke (offener
Code-Fence, halbe Tabelle, unfertige `$$`-Formel) sauber statt zu
flackern (`parseIncompleteMarkdown`, default `true`) — das adressiert die
„live rendern"-Entscheidung direkt. GFM, Mathe (remark-math/rehype-katex)
und Output-Sanitisierung sind eingebaut. Passt zum vorhandenen
Vercel/Next-Stack.

Verworfene Alternativen:
- **react-markdown-Stack** (react-markdown + remark-gfm + remark-math +
  rehype-katex + katex): erprobt, aber nicht streaming-optimiert; mehr
  manuelles Setup und eigene Flacker-Behandlung nötig.
- **markdown-it + dangerouslySetInnerHTML**: braucht zwingend manuelle
  Sanitisierung (DOMPurify), passt schlecht zu React/Streaming.

## Architektur / Änderungen

### 1. Abhängigkeiten (`frontend/package.json`)
- `streamdown` — Renderer (bringt remark-gfm, remark-math, rehype-katex,
  Sanitisierung und Shiki mit).
- `katex` — liefert das CSS (`katex/dist/katex.min.css`) für die
  Formel-Glyphen.
- `package-lock.json` mit committen (CI-Install schlägt sonst fehl).

### 2. CSS-/Tailwind-Integration (`frontend/app/globals.css`)
Tailwind v4 ist CSS-first (`@import "tailwindcss"`, `@theme inline`), es
gibt keine JS-Config.
- `@source "../node_modules/streamdown/dist/index.js";` — damit Tailwind
  die von streamdown genutzten Utility-Klassen mitgeneriert (sonst bleibt
  der Output ungestylt).
- `@import "katex/dist/katex.min.css";` — Formel-Darstellung.

### 3. Rendering (`frontend/components/workbench/CopilotStrip.tsx`)
Nur `AssistantBubble` ändern:
- `{content}` ersetzen durch `<Streamdown>{content}</Streamdown>`.
- `parseIncompleteMarkdown` bleibt default `true` (Streaming-robust).
- Sicherheits-Props: `allowedImagePrefixes={[]}`,
  `allowedLinkPrefixes={["https"]}` — Copilot ist Text-Advisory; keine
  Bilder/aktiven Nicht-HTTPS-Links.
- Der blinkende Streaming-Cursor (`isStreaming`) bleibt erhalten,
  positioniert nach dem Streamdown-Block.
- `whitespace-pre-wrap` an der Bubble entfällt für den gerenderten
  Inhalt (Markdown steuert das Layout selbst).

`UserBubble` bleibt **unverändert** (Klartext).

### 4. Styling-Einpassung
- Streamdown in einen Wrapper kapseln, der die Bubble-Constraints erbt:
  `text-[13px]`, `text-foreground`, `max-w-[80%]`, dunkles Theme.
- Code-Blöcke und Tabellen an Theme-Tokens angleichen
  (`--color-card`, `--color-border`). Ziel: liest sich wie die restliche
  UI, kein Fremdkörper.
- Innenabstände der Bubble so anpassen, dass Block-Elemente
  (Überschrift, Liste) nicht an den Bubble-Rändern kleben.

## Tests (`frontend/__tests__/CopilotStrip.test.tsx`, vitest + jsdom)

> Node 22 verwenden (`nvm use 22`) — Node ≥24 bricht jsdom localStorage.

**TDD — erst rote Tests fürs neue Verhalten:**
1. **Markdown rendert:** Assistant-Content mit `**bold**`, einer
   Liste (`- a\n- b`) und Inline-`` `code` `` → DOM enthält `<strong>`,
   `<li>` (mind. 2), `<code>`.
2. **LaTeX rendert:** Content mit `$E=mc^2$` → DOM enthält ein
   KaTeX-Element (`.katex`).
3. **User bleibt Klartext:** `UserBubble` mit `**x**` → kein `<strong>`,
   literaler Text `**x**` vorhanden.
4. **Streaming-Pfad:** Assistant-Bubble mit `isStreaming` + partiellem
   Markdown rendert ohne Fehler und zeigt den Cursor.

Bestehende Tests, die auf wörtliche Klartext-Gleichheit der
Assistant-Bubble prüfen, werden auf die gerenderte Variante angepasst
(Inhalt weiterhin per Text-Query auffindbar).

## Risiken / offene Punkte

- **Shiki async:** Syntax-Highlighting kommt asynchron; in Tests nur auf
  Text-Präsenz prüfen, nicht auf Highlight-Spans.
- **KaTeX in jsdom:** rendert zu `.katex`-Spans; sollte in jsdom
  funktionieren — falls nicht, Test auf vorhandene Mathe-Container-Klasse
  lockern (nicht die Funktion deaktivieren).
- **Bundle-Größe:** streamdown + Shiki + KaTeX-CSS erhöhen das Frontend-
  Bundle. Akzeptiert (Vercel-Stack, lazy wo möglich).

## Workflow

- Branch: `feat/gh-<N>-copilot-markdown` (N = noch zu erstellende
  GH-Feature-Issue).
- Frontend-only, neue Dependency → Branch + PR (CLAUDE.md).
- Reihenfolge: Spec (dieses Dokument) → GH-Issue → `/supercycle-implement`
  (TDD, Review, Merge).

## Out of Scope

- Backend/`/copilot/stream`-Änderungen.
- Markdown in User-Bubbles.
- Konfigurierbares Highlighting-Theme / Theme-Switcher.
- Bild- oder Datei-Embeds im Chat.
