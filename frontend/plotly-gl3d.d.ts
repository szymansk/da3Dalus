declare module "plotly.js-gl3d-dist-min" {
  interface PlotlyStatic {
    react(
      root: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ): Promise<void>;
    newPlot(
      root: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ): Promise<void>;
    relayout(root: HTMLElement, update: Record<string, unknown>): Promise<void>;
    restyle(
      root: HTMLElement,
      update: Record<string, unknown>,
      indices?: number[],
    ): Promise<void>;
    purge(root: HTMLElement): void;
  }
  const Plotly: PlotlyStatic;
  export default Plotly;
  export const react: PlotlyStatic["react"];
  export const newPlot: PlotlyStatic["newPlot"];
  export const relayout: PlotlyStatic["relayout"];
  export const restyle: PlotlyStatic["restyle"];
  export const purge: PlotlyStatic["purge"];
}
