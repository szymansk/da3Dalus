import type { languages, editor } from "monaco-editor";

export const avlLanguage: languages.IMonarchLanguage & { keywords: string[] } = {
  keywords: [
    "SURFACE",
    "SECTION",
    "YDUPLICATE",
    "AFIL",
    "AFILE",
    "CLAF",
    "CDCL",
    "CONTROL",
    "BODY",
    "BFIL",
    "BFILE",
    "COMPONENT",
    "ANGLE",
    "SCALE",
    "TRANSLATE",
    "NOWAKE",
    "NOALBE",
    "NOLOAD",
    "NACA",
    "DESIGN",
    "INDEX",
  ],
  tokenizer: {
    root: [
      [/[!#][^\n]*/, "comment"],
      [
        /[A-Z][A-Z_]+/,
        { cases: { "@keywords": "keyword", "@default": "identifier" } },
      ],
      [/-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?/, "number"],
      [/[a-zA-Z_]\w*/, "identifier"],
    ],
  },
};

export const avlTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "keyword", foreground: "FF8400", fontStyle: "bold" },
    { token: "comment", foreground: "7A7B78", fontStyle: "italic" },
    { token: "number", foreground: "30A46C" },
    { token: "identifier", foreground: "B8B9B6" },
  ],
  colors: {
    "editor.background": "#1A1A1A",
    "editor.foreground": "#FFFFFF",
    "editor.lineHighlightBackground": "#2A2A30",
    "editorLineNumber.foreground": "#7A7B78",
    "editor.selectionBackground": "#FF840033",
    "editorCursor.foreground": "#FF8400",
  },
};
