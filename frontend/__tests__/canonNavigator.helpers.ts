import { readFileSync } from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

/** The generated canon navigator, exactly as the Expert View serves it. */
const PAGE = readFileSync(
  path.resolve(__dirname, "../public/canon-navigator.html"),
  "utf-8",
);

export type NavWindow = Window & typeof globalThis;

export interface Reply {
  status?: number;
  body: unknown;
}

export type Route = (url: string, init?: RequestInit) => Reply | Promise<Reply>;

export interface Calls {
  url: string;
  init?: RequestInit;
  body?: Record<string, unknown>;
}

/** Wait until pending promises and zero-delay timers have run. */
export async function settle(rounds = 4): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

/**
 * Open the navigator in jsdom with a stubbed backend.
 * @param query The query string of the page (connected mode or none).
 * @param route Answers each request of the page.
 */
export function openNavigator(query: string, route: Route) {
  const calls: Calls[] = [];
  const dom = new JSDOM(PAGE, {
    url: `http://expert.test/canon-navigator.html${query}`,
    runScripts: "dangerously",
    pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        calls.push({
          url,
          init,
          body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
        });
        const reply = await route(url, init);
        const status = reply.status ?? 200;
        return {
          ok: status < 400,
          status,
          json: async () => reply.body,
        } as Response;
      }) as typeof window.fetch;
    },
  });
  const { window } = dom;
  return {
    window,
    document: window.document,
    calls,
    /** The SVG group of a node (quantity or rule id). */
    node: (id: string) =>
      window.eval(`nodeEls[${JSON.stringify(id)}]`) as SVGGElement,
    click: (element: Element) =>
      element.dispatchEvent(new window.MouseEvent("click", { bubbles: true })),
  };
}
