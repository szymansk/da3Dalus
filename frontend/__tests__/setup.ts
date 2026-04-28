import "@testing-library/jest-dom";

/**
 * Vitest setup — polyfill HTMLDialogElement for jsdom.
 *
 * jsdom does not implement `showModal()` or `close()` on `<dialog>`.
 * We add minimal stubs so the `useDialog` hook works in unit tests.
 */

if (typeof HTMLDialogElement !== "undefined") {
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}
