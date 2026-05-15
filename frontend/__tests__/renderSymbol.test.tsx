import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import React from "react";

import { renderSymbol } from "@/components/workbench/renderSymbol";

function html(node: React.ReactNode): string {
  const { container } = render(<>{node}</>);
  return container.innerHTML;
}

describe("renderSymbol", () => {
  it("passes through labels with no underscore", () => {
    expect(html(renderSymbol("MAC"))).toBe("MAC");
    expect(html(renderSymbol("Re"))).toBe("Re");
    expect(html(renderSymbol("CG"))).toBe("CG");
  });

  it("renders single underscore as subscript", () => {
    expect(html(renderSymbol("V_x"))).toBe('V<sub class="text-[9px]">x</sub>');
    expect(html(renderSymbol("V_y"))).toBe('V<sub class="text-[9px]">y</sub>');
    expect(html(renderSymbol("V_a"))).toBe('V<sub class="text-[9px]">a</sub>');
  });

  it("renders multi-underscore subscript with inner underscores → commas", () => {
    expect(html(renderSymbol("V_min_sink"))).toBe(
      'V<sub class="text-[9px]">min,sink</sub>',
    );
  });

  it("keeps trailing non-word characters outside the subscript", () => {
    expect(html(renderSymbol("V_cruise*"))).toBe(
      'V<sub class="text-[9px]">cruise</sub>*',
    );
  });

  it("renders multi-letter abbreviations after underscore (V_NE, V_md)", () => {
    expect(html(renderSymbol("V_NE"))).toBe('V<sub class="text-[9px]">NE</sub>');
    expect(html(renderSymbol("V_md"))).toBe('V<sub class="text-[9px]">md</sub>');
    expect(html(renderSymbol("V_max"))).toBe('V<sub class="text-[9px]">max</sub>');
  });

  it("falls back to the original label for malformed input", () => {
    expect(html(renderSymbol(""))).toBe("");
    expect(html(renderSymbol("V_"))).toBe("V_");
  });
});
