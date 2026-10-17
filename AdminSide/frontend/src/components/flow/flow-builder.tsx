"use client";

import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MiniMap, Panel,
  addEdge, useNodesState, useEdgesState, useReactFlow,
  type Node, type Edge, type Connection,
} from "@xyflow/react";
import { flowsApi, type FlowNode } from "@/lib/flows/browser";
import { BuilderContext } from "@/components/flow/builder-context";
import { MessageNode } from "@/components/flow/message-node";
import { NodeEditor } from "@/components/flow/node-editor";

const nodeTypes = { message: MessageNode };

function sanitize(nodes: Node[]): FlowNode[] {
  return nodes.map((n) => ({ id: n.id, type: n.type ?? "message", position: n.position, data: n.data as FlowNode["data"] }));
}
function sanitizeEdges(edges: Edge[]) {
  return edges.map((e) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle ?? null, targetHandle: e.targetHandle ?? null }));
}

function BuilderInner({ flowId }: { flowId: string }) {
  const router = useRouter();
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"draft" | "active">("draft");
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  useEffect(() => { nodesRef.current = nodes; }, [nodes]);
  useEffect(() => { edgesRef.current = edges; }, [edges]);

  const past = useRef<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const future = useRef<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const [, force] = useState(0);
  const snapshot = useCallback(() => {
    past.current.push({ nodes: nodesRef.current, edges: edgesRef.current });
    if (past.current.length > 100) past.current.shift();
    future.current = [];
    force((x) => x + 1);
  }, []);

  useEffect(() => {
    flowsApi.get(flowId)
      .then((f) => {
        setName(f.name);
        setStatus(f.status);
        setNodes((f.nodes ?? []) as unknown as Node[]);
        setEdges((f.edges ?? []) as unknown as Edge[]);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load flow."))
      .finally(() => setLoading(false));
  }, [flowId, setNodes, setEdges]);

  const onEdit = useCallback((id: string) => {
    setSelectedId(id);
    setNodes((nds) => nds.map((n) => ({ ...n, selected: n.id === id })));
  }, [setNodes]);

  const onDelete = useCallback((id: string) => {
    snapshot();
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
    setSelectedId((cur) => (cur === id ? null : cur));
  }, [snapshot, setNodes, setEdges]);

  const onDuplicate = useCallback((id: string) => {
    snapshot();
    const src = nodesRef.current.find((n) => n.id === id);
    if (!src) return;
    const newId = `n_${Date.now()}`;
    const clone: Node = { ...src, id: newId, position: { x: src.position.x + 48, y: src.position.y + 64 }, data: { ...src.data, isStart: false }, selected: false };
    setNodes((nds) => [...nds.map((n) => ({ ...n, selected: false })), clone]);
    setSelectedId(newId);
  }, [snapshot, setNodes]);

  const onConnect = useCallback((c: Connection) => {
    snapshot();
    setEdges((eds) => addEdge({ ...c, id: `e_${Date.now()}` }, eds));
  }, [snapshot, setEdges]);

  const addNode = useCallback(() => {
    snapshot();
    const newId = `n_${Date.now()}`;
    const node: Node = {
      id: newId, type: "message",
      position: { x: 220 + Math.random() * 120, y: 280 + Math.random() * 120 },
      data: { label: "Text Message", channel: "whatsapp", messageType: "text", message: "" },
    };
    setNodes((nds) => [...nds.map((n) => ({ ...n, selected: false })), node]);
    setSelectedId(newId);
  }, [snapshot, setNodes]);

  const changeNodeData = useCallback((patch: Record<string, unknown>) => {
    if (!selectedId) return;
    snapshot();
    setNodes((nds) => nds.map((n) => (n.id === selectedId ? { ...n, data: { ...n.data, ...patch } } : n)));
  }, [selectedId, snapshot, setNodes]);

  const undo = useCallback(() => {
    const prev = past.current.pop();
    if (!prev) return;
    future.current.push({ nodes: nodesRef.current, edges: edgesRef.current });
    setNodes(prev.nodes); setEdges(prev.edges); force((x) => x + 1);
  }, [setNodes, setEdges]);
  const redo = useCallback(() => {
    const next = future.current.pop();
    if (!next) return;
    past.current.push({ nodes: nodesRef.current, edges: edgesRef.current });
    setNodes(next.nodes); setEdges(next.edges); force((x) => x + 1);
  }, [setNodes, setEdges]);

  async function save() {
    setSaving(true);
    try {
      await flowsApi.update(flowId, { name: name.trim() || "Untitled flow", nodes: sanitize(nodesRef.current), edges: sanitizeEdges(edgesRef.current) });
      setToast("Saved");
      setTimeout(() => setToast(""), 1800);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Save failed");
      setTimeout(() => setToast(""), 2500);
    } finally {
      setSaving(false);
    }
  }
  async function toggleStatus() {
    const next = status === "active" ? "draft" : "active";
    try { await flowsApi.update(flowId, { status: next }); setStatus(next); }
    catch (e) { setToast(e instanceof Error ? e.message : "Failed"); setTimeout(() => setToast(""), 2500); }
  }

  const selectedNode = (nodes.find((n) => n.id === selectedId) as unknown as FlowNode) ?? null;

  if (loading) return <div className="fixed inset-0 z-40 flex items-center justify-center bg-white text-sm text-slate-500">Loading flow…</div>;

  return (
    <BuilderContext.Provider value={{ onEdit, onDuplicate, onDelete, selectedId }}>
      <div className="fixed inset-0 z-40 flex flex-col bg-slate-50">
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/flow")} className="text-sm font-semibold text-slate-600 hover:text-slate-900">‹ Flow</button>
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-56 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold outline-none focus:border-blue-500" />
            <button onClick={() => void toggleStatus()} className={`rounded-full px-3 py-1 text-xs font-semibold ${status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
              {status === "active" ? "● Active" : "○ Draft"}
            </button>
          </div>
          <div className="flex items-center gap-2">
            {toast && <span className="text-xs font-semibold text-emerald-600">{toast}</span>}
            <button onClick={undo} disabled={past.current.length === 0} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-600 disabled:opacity-40">↶ Undo</button>
            <button onClick={redo} disabled={future.current.length === 0} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-600 disabled:opacity-40">↷ Redo</button>
            <button onClick={() => void save()} disabled={saving} className="rounded-lg bg-blue-600 px-5 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">{saving ? "Saving…" : "Save"}</button>
          </div>
        </div>

        {error && <p role="alert" className="bg-rose-50 px-4 py-2 text-sm text-rose-800">{error}</p>}

        <div className="flex min-h-0 flex-1">
          {selectedNode && (
            <NodeEditor
              node={selectedNode}
              onChange={changeNodeData}
              onClose={() => { setSelectedId(null); setNodes((nds) => nds.map((n) => ({ ...n, selected: false }))); }}
              onDuplicate={() => selectedId && onDuplicate(selectedId)}
            />
          )}
          <div className="relative min-w-0 flex-1">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              onPaneClick={() => { setSelectedId(null); setNodes((nds) => nds.map((n) => ({ ...n, selected: false }))); }}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={18} color="#e2e8f0" />
              <Controls showInteractive={false} />
              <MiniMap pannable zoomable className="!bottom-4 !right-4" />
              <Panel position="bottom-center">
                <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1.5 shadow-md">
                  <button onClick={() => fitView({ duration: 300 })} title="Fit view" className="rounded-lg px-2.5 py-1.5 text-slate-600 hover:bg-slate-100">⤢</button>
                  <button onClick={() => zoomIn({ duration: 200 })} title="Zoom in" className="rounded-lg px-2.5 py-1.5 text-slate-600 hover:bg-slate-100">＋</button>
                  <button onClick={() => zoomOut({ duration: 200 })} title="Zoom out" className="rounded-lg px-2.5 py-1.5 text-slate-600 hover:bg-slate-100">－</button>
                  <button onClick={addNode} title="Add node" className="rounded-lg bg-blue-600 px-3 py-1.5 font-semibold text-white hover:bg-blue-700">＋ Node</button>
                </div>
              </Panel>
            </ReactFlow>
          </div>
        </div>
      </div>
    </BuilderContext.Provider>
  );
}

export function FlowBuilder({ flowId }: { flowId: string }) {
  return (
    <ReactFlowProvider>
      <BuilderInner flowId={flowId} />
    </ReactFlowProvider>
  );
}
