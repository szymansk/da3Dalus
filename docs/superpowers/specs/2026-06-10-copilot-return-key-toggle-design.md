# Design: Umschaltbares Return-Verhalten im Copilot-Chat

**Datum:** 2026-06-10
**Scope:** Frontend-only
**Status:** Spec — wartet auf Review

## Problem

Im Copilot-Chat (`frontend/components/workbench/CopilotStrip.tsx`) schickt
heute **Cmd/Ctrl+Enter** die Nachricht ab; **Enter** erzeugt eine neue
Zeile. Nutzer erwarten teils das umgekehrte Chat-Standardverhalten (Enter
schickt ab), teils ein reines Mehrzeilen-Eingabefeld (Enter = neue Zeile).
Es gibt keine Möglichkeit, zwischen beiden zu wählen.

## Ziel

Zwei umschaltbare Modi mit einem Toggle-Button, Auswahl persistent:

| Modus | Shift+Enter | Enter | Cmd/Ctrl+Enter |
|---|---|---|---|
| **Default** (`enterToSend = true`) | neue Zeile | **abschicken** | abschicken |
| **Alternativ** (`enterToSend = false`) | neue Zeile | neue Zeile | abschicken |

In **beiden** Modi schickt der Send-Button und Cmd/Ctrl+Enter ab.

## Entscheidungen (mit User abgestimmt)

- Senden im Alt-Modus: **Send-Button + Cmd/Ctrl+Enter** bleiben aktiv (kein
  reiner Button-only-Modus).
- Persistenz: **localStorage**, Default beim ersten Mal `enterToSend = true`.

## Architektur / Änderungen

Alles in `frontend/components/workbench/CopilotStrip.tsx` plus ein kleiner
lokaler Hook.

### 1. Hook `useEnterToSend()`
Kapselt State + Persistenz nach dem Muster von `AeroplaneContext`:
- `useState(true)` (Default, damit SSR/erster Render deterministisch ist —
  kein Hydration-Mismatch).
- `useEffect` beim Mount: liest `localStorage`-Key `copilot:enter-to-send`
  (`"true"`/`"false"`), setzt State falls vorhanden.
- `toggle()` flippt den State und schreibt den neuen Wert nach localStorage.
- Rückgabe: `{ enterToSend, toggle }`.
- localStorage-Zugriffe defensiv (try/catch / `typeof window` guard), damit
  Tests und SSR nicht brechen.

### 2. Tastaturlogik (`handleKeyDown` der Textarea)
Reihenfolge der Prüfungen:
1. `e.nativeEvent.isComposing` → nichts tun (IME-Eingabe nicht stören).
2. `e.key === "Enter" && (e.metaKey || e.ctrlKey)` → `preventDefault()` +
   `handleSend()` (beide Modi).
3. `e.key === "Enter" && e.shiftKey` → nichts tun (Default: neue Zeile).
4. `e.key === "Enter"` (allein) → wenn `enterToSend`: `preventDefault()` +
   `handleSend()`; sonst nichts tun (neue Zeile).

### 3. Toggle-Button
- In der Input-Fußzeile (bei Status-Text / Send-Button).
- `type="button"`, `aria-pressed={enterToSend}`, `title`/`aria-label`
  spiegelt den Modus.
- Icon: lucide `CornerDownLeft`. Sichtbares Kurzlabel optional, primär
  Icon + Tooltip; gleicher Stil wie die übrigen Footer-Buttons.
- `onClick` → `toggle()`.

### 4. Hinweistext
Der bestehende `<span>` neben dem Send-Button wird modusabhängig:
- Default: „Enter to send · Shift+Enter for newline"
- Alt: „Shift+Enter / Enter for newline · Cmd+Enter to send"
Während `isSending` weiterhin „Copilot is responding…".

## Tests (`frontend/__tests__/CopilotStrip.test.tsx`, vitest + jsdom)

> Node 22 (`nvm use 22`).

TDD — erst rote Tests:
1. **Default-Modus:** Enter (ohne Modifier) ruft `sendMessage` mit dem Text
   auf; Shift+Enter ruft `sendMessage` **nicht** auf; Cmd/Ctrl+Enter ruft
   `sendMessage` auf.
2. **Alt-Modus** (Toggle vorher umgeschaltet bzw. localStorage `false`):
   Enter ruft `sendMessage` **nicht** auf; Cmd/Ctrl+Enter ruft auf;
   Send-Button ruft auf.
3. **Toggle:** Klick flippt `aria-pressed`; schreibt `copilot:enter-to-send`
   nach localStorage; beim Mount mit gesetztem localStorage-Wert startet der
   passende Modus.
4. **A11y:** Toggle-Button hat `aria-pressed` passend zum Zustand und ein
   `aria-label`.
5. **IME:** Enter mit `isComposing=true` ruft `sendMessage` **nicht** auf.

localStorage wird pro Test zurückgesetzt (`beforeEach`).

## Risiken / offene Punkte

- jsdom + Node ≥24 bricht localStorage (bekannt) → Tests auf Node 22.
- `isComposing` muss im Test über das `KeyboardEvent` simuliert werden
  (`fireEvent.keyDown(el, { key: "Enter", isComposing: true })` bzw. über
  `nativeEvent`).

## Workflow

- Branch: `feat/gh-<N>-copilot-return-toggle` (N = neue GH-Feature-Issue).
- Frontend-only Verhaltensänderung → Branch + PR, Supercycle
  (TDD → Review → Merge), wie #930.

## Out of Scope

- Globale Tastatur-Einstellungen außerhalb des Copilot-Inputs.
- Backend/Persistenz serverseitig (rein clientseitig via localStorage).
- Konfigurierbare weitere Tastenkürzel.
