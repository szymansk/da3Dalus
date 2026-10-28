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
 * @param basePath The app's base path (a preview stage serves it under one); a public file is not
 *   prefixed by Next.js when it is the `src` of an iframe.
 */
export function canonNavigatorUrl(
  apiBase: string,
  aircraftId: string,
  basePath: string = process.env.NEXT_PUBLIC_BASE_PATH ?? "",
): string {
  const query = new URLSearchParams({
    connected: "1",
    api: apiBase,
    aircraft: aircraftId,
  });
  return `${basePath}${CANON_NAVIGATOR_PATH}?${query.toString()}`;
}
