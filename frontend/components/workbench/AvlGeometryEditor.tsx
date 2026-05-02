"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { X, Maximize2, Minimize2, Save, RotateCcw } from "lucide-react";
import dynamic from "next/dynamic";
import { useDialog } from "@/hooks/useDialog";
import { useAvlGeometry } from "@/hooks/useAvlGeometry";
import { AvlDirtyWarning } from "./AvlDirtyWarning";

const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
  loading: () => (
    <div className="flex flex-1 items-center justify-center text-[13px] text-muted-foreground">
      Loading editor…
    </div>
  ),
});

const MonacoDiffEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-1 items-center justify-center text-[13px] text-muted-foreground">
        Loading diff editor…
      </div>
    ),
  },
);

interface Props {
  readonly aeroplaneId: string;
  readonly open: boolean;
  readonly onClose: () => void;
}

type EditorMode = "edit" | "diff";

export function AvlGeometryEditor({ aeroplaneId, open, onClose }: Props) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const geometry = useAvlGeometry(open ? aeroplaneId : null);

  const [localContent, setLocalContent] = useState("");
  const [regeneratedContent, setRegeneratedContent] = useState<string | null>(null);
  const [mode, setMode] = useState<EditorMode>("edit");
  const [fullscreen, setFullscreen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showDirtyWarning, setShowDirtyWarning] = useState(false);
  const monacoRef = useRef<unknown>(null);

  useEffect(() => {
    if (geometry.content !== null && localContent === "") {
      setLocalContent(geometry.content);
    }
  }, [geometry.content, localContent]);

  useEffect(() => {
    if (open && geometry.isDirty && geometry.isUserEdited) {
      setShowDirtyWarning(true);
    }
  }, [open, geometry.isDirty, geometry.isUserEdited]);

  useEffect(() => {
    if (!open) {
      setLocalContent("");
      setRegeneratedContent(null);
      setMode("edit");
      setFullscreen(false);
      setShowDirtyWarning(false);
    }
  }, [open]);

  function handleEditorDidMount(editor: unknown, monaco: unknown) {
    monacoRef.current = monaco;
    const m = monaco as typeof import("monaco-editor");
    import("./avlLanguage").then(({ avlLanguage, avlTheme }) => {
      m.languages.register({ id: "avl" });
      m.languages.setMonarchTokensProvider("avl", avlLanguage);
      m.editor.defineTheme("avl-dark", avlTheme);
      m.editor.setTheme("avl-dark");
    });
  }

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const contentToSave = mode === "diff" && regeneratedContent !== null
        ? regeneratedContent
        : localContent;
      await geometry.save(contentToSave);
      onClose();
    } catch {
      // error is set in hook
    } finally {
      setSaving(false);
    }
  }, [geometry, localContent, regeneratedContent, mode, onClose]);

  const handleRegenerate = useCallback(async () => {
    setShowDirtyWarning(false);
    try {
      const fresh = await geometry.regenerate();
      setLocalContent(fresh);
      setMode("edit");
    } catch {
      // error is set in hook
    }
  }, [geometry]);

  const handleViewDiff = useCallback(async () => {
    setShowDirtyWarning(false);
    try {
      const fresh = await geometry.regenerate();
      setRegeneratedContent(fresh);
      setMode("diff");
    } catch {
      // error is set in hook
    }
  }, [geometry]);

  const handleReset = useCallback(async () => {
    try {
      const fresh = await geometry.regenerate();
      setLocalContent(fresh);
      setMode("edit");
    } catch {
      // error is set in hook
    }
  }, [geometry]);

  const sizeClasses = fullscreen
    ? "fixed inset-4 z-50"
    : "w-[900px] h-[650px]";

  function renderEditorBody() {
    if (geometry.isLoading) {
      return (
        <div className="flex h-full items-center justify-center text-[13px] text-muted-foreground">
          Loading AVL geometry…
        </div>
      );
    }
    if (mode === "diff" && regeneratedContent !== null) {
      return (
        <MonacoDiffEditor
          original={localContent}
          modified={regeneratedContent}
          language="avl"
          theme="avl-dark"
          onMount={handleEditorDidMount}
          options={{
            readOnly: false,
            renderSideBySide: true,
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: 13,
            minimap: { enabled: false },
            lineNumbers: "on",
            scrollBeyondLastLine: false,
          }}
        />
      );
    }
    return (
      <MonacoEditor
        value={localContent}
        onChange={(v) => setLocalContent(v ?? "")}
        language="avl"
        theme="avl-dark"
        onMount={handleEditorDidMount}
        options={{
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: 13,
          minimap: { enabled: false },
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          wordWrap: "off",
          automaticLayout: true,
        }}
      />
    );
  }

  return (
    <>
      <AvlDirtyWarning
        open={showDirtyWarning}
        onClose={() => setShowDirtyWarning(false)}
        onViewDiff={handleViewDiff}
        onRegenerate={handleRegenerate}
      />

      <dialog
        ref={dialogRef}
        className="m-auto bg-transparent backdrop:bg-black/60"
        onClose={handleClose}
        aria-label="AVL Geometry Editor"
      >
        <div
          className={`flex flex-col rounded-xl border border-border bg-card shadow-2xl ${sizeClasses}`}
        >
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-4 py-3">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
              {mode === "diff" ? "AVL Geometry — Diff View" : "AVL Geometry Editor"}
            </span>
            {geometry.isUserEdited && (
              <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] text-primary">
                User Edited
              </span>
            )}
            <div className="flex-1" />
            {mode === "diff" && (
              <button
                onClick={() => setMode("edit")}
                className="rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
              >
                Back to Editor
              </button>
            )}
            <button
              onClick={() => setFullscreen((f) => !f)}
              className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <button
              onClick={onClose}
              className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={14} />
            </button>
          </div>

          {/* Editor Body */}
          <div className="flex-1 overflow-hidden">
            {renderEditorBody()}
          </div>

          {/* Footer */}
          <div className="flex items-center gap-2 border-t border-border px-4 py-3">
            {geometry.error && (
              <p className="text-[12px] text-destructive">{geometry.error}</p>
            )}
            <div className="flex-1" />
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3.5 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent"
            >
              <RotateCcw size={12} />
              Reset to Generated
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
            >
              <Save size={12} />
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </dialog>
    </>
  );
}
