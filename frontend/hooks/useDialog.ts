import { useRef, useEffect, useCallback } from "react";

/**
 * Manages a native `<dialog>` element's open/close lifecycle via
 * `.showModal()` and `.close()`.
 *
 * Returns a `ref` to attach to the `<dialog>` element and a stable
 * `handleClose` callback suitable for the `onClose` event handler.
 *
 * Usage:
 * ```tsx
 * const { dialogRef, handleClose } = useDialog(open, onClose);
 * return (
 *   <dialog ref={dialogRef} onClose={handleClose} ...>
 *     ...
 *   </dialog>
 * );
 * ```
 */
export function useDialog(open: boolean, onClose: () => void) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    if (open && !el.open) {
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  return { dialogRef, handleClose } as const;
}
