/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    /* ── Layer rules ─────────────────────────────────────────── */
    {
      name: "no-circular",
      severity: "error",
      comment: "No circular dependencies allowed",
      from: {},
      to: { circular: true },
    },
    {
      name: "no-hooks-import-components",
      severity: "warn",
      comment: "Hooks should not import from components/ — invert the dependency",
      from: { path: "^hooks/" },
      to: { path: "^components/" },
    },
    {
      name: "no-lib-import-components",
      severity: "warn",
      comment: "Lib utilities should not import from components/ or hooks/",
      from: { path: "^lib/" },
      to: { path: "^(components|hooks)/" },
    },
    {
      name: "no-components-import-app",
      severity: "error",
      comment: "Components must not import from app/ routes — wrong dependency direction",
      from: { path: "^components/" },
      to: { path: "^app/" },
    },
    {
      name: "no-hooks-import-app",
      severity: "error",
      comment: "Hooks must not import from app/ routes",
      from: { path: "^hooks/" },
      to: { path: "^app/" },
    },

    /* ── Orphan detection ────────────────────────────────────── */
    {
      name: "no-orphans",
      severity: "info",
      comment: "Files that are not imported by anything",
      from: { orphan: true, pathNot: ["\\.(test|spec)\\.", "e2e/", "\\.d\\.ts$", "page\\.tsx$", "layout\\.tsx$"] },
      to: {},
    },
  ],
  options: {
    doNotFollow: {
      path: "node_modules",
    },
    exclude: {
      path: ["node_modules", "\\.next", "\\.features-gen", "e2e"],
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: "tsconfig.json",
    },
    enhancedResolveOptions: {
      exportsFields: ["exports"],
      conditionNames: ["import", "require", "node", "default"],
    },
    reporterOptions: {
      text: {
        highlightFocused: true,
      },
    },
  },
};
