/**
 * Where the Expert View finds the canon navigator and how it connects it to the backend.
 *
 * The navigator is the generated page `public/canon-navigator.html`; with `connected=1` it computes
 * a clicked quantity through the backend for the aircraft given (gh-1282, ADR 0030).
 */

export const CANON_NAVIGATOR_PATH = "/canon-navigator.html";

/**
 * The address of the connected navigator for one aircraft.
 * @param apiBase The backend's base address, as the app's fetcher uses it.
 * @param aircraftId A fleet identifier from GET /canon/fleet.
 */
export function canonNavigatorUrl(apiBase: string, aircraftId: string): string {
  const query = new URLSearchParams({
    connected: "1",
    api: apiBase,
    aircraft: aircraftId,
  });
  return `${CANON_NAVIGATOR_PATH}?${query.toString()}`;
}
