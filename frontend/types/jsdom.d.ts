// Minimal declaration of the part of jsdom the navigator test uses (no @types/jsdom in the project).
declare module "jsdom" {
  export interface JSDOMOptions {
    url?: string;
    runScripts?: "dangerously" | "outside-only";
    pretendToBeVisual?: boolean;
    beforeParse?: (window: Window & typeof globalThis) => void;
  }

  export class JSDOM {
    constructor(html?: string, options?: JSDOMOptions);
    readonly window: Window & typeof globalThis;
  }
}
