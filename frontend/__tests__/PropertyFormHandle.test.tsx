import { describe, it, expect, vi } from "vitest";
import { render, act } from "@testing-library/react";
import React, { useRef, useImperativeHandle, forwardRef } from "react";

interface SaveHandle {
  save(): Promise<void>;
}

const MockForm = forwardRef<SaveHandle, { onSave: () => Promise<void>; dirty: boolean }>(
  function MockForm({ onSave, dirty }, ref) {
    useImperativeHandle(ref, () => ({
      async save() {
        if (!dirty) return;
        await onSave();
      },
    }), [dirty, onSave]);
    return <div>form</div>;
  },
);

function Harness({ onSave, dirty }: { onSave: () => Promise<void>; dirty: boolean }) {
  const ref = useRef<SaveHandle>(null);
  return (
    <>
      <MockForm ref={ref} onSave={onSave} dirty={dirty} />
      <button onClick={() => { ref.current?.save().catch(() => {}); }}>trigger-save</button>
    </>
  );
}

describe("imperative save handle", () => {
  it("calls onSave when dirty", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { getByText } = render(<Harness onSave={onSave} dirty={true} />);
    await act(async () => { getByText("trigger-save").click(); });
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("skips save when not dirty", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { getByText } = render(<Harness onSave={onSave} dirty={false} />);
    await act(async () => { getByText("trigger-save").click(); });
    expect(onSave).not.toHaveBeenCalled();
  });
});
