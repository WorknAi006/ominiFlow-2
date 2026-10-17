"use client";

import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MiniMap, Panel,
  addEdge, useNodesState, useEdgesState, useReactFlow,
  type Node, type Edge, type Connection,
} from "@xyflow/react";
import { flowsApi, type FlowNode, MESSAGE_TYPES } from "@/lib/flows/browser";
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
  const [addMenuOpen, setAddMenuOpen] = useState(false);

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
    setEdges((eds) => addEdge({ ...c, id: `e_${Date.now()}`, type: "smoothstep" }, eds));
  }, [snapshot, setEdges]);

  const addTypedNode = useCallback((messageType: string = "text") => {
    snapshot();
    const newId = `n_${Date.now()}`;
    const typeLabel = MESSAGE_TYPES.find((t) => t.value === messageType)?.label ?? "Message";
    
    // Initial data tailored to node type
    const initialData: Record<string, unknown> = {
      label: typeLabel,
      channel: "whatsapp",
      messageType,
      message: "",
    };

    if (messageType === "button") {
      initialData.buttons = [
        { id: `b_${Date.now()}_1`, title: "Option 1", kind: "reply" },
        { id: `b_${Date.now()}_2`, title: "Option 2", kind: "reply" },
      ];
    } else if (messageType === "list") {
      initialData.listMenuButton = "Options";
      initialData.listItems = [
        { id: `i_${Date.now()}_1`, title: "Option 1" },
        { id: `i_${Date.now()}_2`, title: "Option 2" },
      ];
    } else if (messageType === "condition") {
      initialData.condition = { source: "last_input", operator: "is", value: "" };
    } else if (messageType === "delay") {
      initialData.delayValue = 5;
      initialData.delayUnit = "minutes";
    }

    const node: Node = {
      id: newId,
      type: "message",
      position: { x: 300 + Math.random() * 80, y: 150 + Math.random() * 80 },
      data: initialData,
    };
    setNodes((nds) => [...nds.map((n) => ({ ...n, selected: false })), node]);
    setSelectedId(newId);
    setAddMenuOpen(false);
  }, [snapshot, setNodes]);

  const changeNodeData = useCallback((patch: Record<string, unknown>) => {
    if (!selectedId) return;
    snapshot();
    setNodes((nds) => nds.map((n) => (n.id === selectedId ? { ...n, data: { ...n.data, ...patch } } : n)));
  }, [selectedId, snapshot, setNodes]);

  // Assisted Auto-Layout: arranges nodes topologically in clean columns
  const autoLayout = useCallback(() => {
    const currentNodes = nodesRef.current;
    const currentEdges = edgesRef.current;
    if (currentNodes.length === 0) return;

    snapshot();

    // Find start node or nodes with no incoming edges
    const inDegree: Record<string, number> = {};
    const adj: Record<string, string[]> = {};
    currentNodes.forEach((n) => {
      inDegree[n.id] = 0;
      adj[n.id] = [];
    });
    currentEdges.forEach((e) => {
      if (inDegree[e.target] !== undefined) inDegree[e.target]++;
      if (adj[e.source]) adj[e.source].push(e.target);
    });

    const startNode = currentNodes.find((n) => Boolean(n.data?.isStart)) ||
      currentNodes.find((n) => inDegree[n.id] === 0) ||
      currentNodes[0];

    // BFS to assign column depths
    const depth: Record<string, number> = {};
    const queue: string[] = [startNode.id];
    depth[startNode.id] = 0;

    while (queue.length > 0) {
      const u = queue.shift()!;
      for (const v of adj[u] || []) {
        if (depth[v] === undefined || depth[v] < depth[u] + 1) {
          depth[v] = depth[u] + 1;
          queue.push(v);
        }
      }
    }

    // Nodes not reached from start
    currentNodes.forEach((n) => {
      if (depth[n.id] === undefined) depth[n.id] = 0;
    });

    // Group nodes by column depth
    const columns: Record<number, Node[]> = {};
    currentNodes.forEach((n) => {
      const col = depth[n.id] ?? 0;
      if (!columns[col]) columns[col] = [];
      columns[col].push(n);
    });

    const HORIZONTAL_GAP = 360;
    const VERTICAL_GAP = 300;
    const START_X = 80;
    const START_Y = 100;

    const positionedNodes = currentNodes.map((n) => {
      const col = depth[n.id] ?? 0;
      const rowIdx = (columns[col] || []).findIndex((x) => x.id === n.id);
      return {
        ...n,
        position: {
          x: START_X + col * HORIZONTAL_GAP,
          y: START_Y + (rowIdx >= 0 ? rowIdx : 0) * VERTICAL_GAP,
        },
      };
    });

    setNodes(positionedNodes);
    setTimeout(() => { fitView({ duration: 400, padding: 0.2 }); }, 50);
  }, [snapshot, setNodes, fitView]);

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
      setToast("Saved successfully");
      setTimeout(() => setToast(""), 2000);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Save failed");
      setTimeout(() => setToast(""), 3000);
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus() {
    const next = status === "active" ? "draft" : "active";
    try {
      await flowsApi.update(flowId, { status: next });
      setStatus(next);
      setToast(next === "active" ? "Flow activated" : "Flow set to draft");
      setTimeout(() => setToast(""), 2000);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Failed");
      setTimeout(() => setToast(""), 2500);
    }
  }

  const selectedNode = (nodes.find((n) => n.id === selectedId) as unknown as FlowNode) ?? null;

  if (loading) return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-50 text-sm font-semibold text-slate-500">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
        <span>Loading workflow canvas...</span>
      </div>
    </div>
  );

  return (
    <BuilderContext.Provider value={{ onEdit, onDuplicate, onDelete, selectedId }}>
      <div className="fixed inset-0 z-40 flex flex-col bg-slate-50 select-none">
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 border-b border-slate-200/90 bg-white px-5 py-3 shadow-xs">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/flow")}
              className="flex items-center gap-1.5 text-sm font-bold text-slate-600 hover:text-slate-900 transition py-1 px-2 rounded-lg hover:bg-slate-100"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              <span>Flow</span>
            </button>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Flow Name..."
              className="w-64 rounded-xl border border-slate-200 px-3.5 py-1.5 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-2xs transition"
            />
            <button
              type="button"
              onClick={() => void toggleStatus()}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold transition shadow-2xs ${
                status === "active" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-100 text-slate-600 border border-slate-200"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${status === "active" ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
              {status === "active" ? "Active" : "Draft"}
            </button>
          </div>

          <div className="flex items-center gap-2.5">
            {toast && (
              <span className="text-xs font-bold text-emerald-600 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg animate-in fade-in">
                {toast}
              </span>
            )}
            <button
              type="button"
              onClick={undo}
              disabled={past.current.length === 0}
              className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-50 disabled:opacity-30 transition"
            >
              <span>↶</span> Undo
            </button>
            <button
              type="button"
              onClick={redo}
              disabled={future.current.length === 0}
              className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-50 disabled:opacity-30 transition"
            >
              <span>↷</span> Redo
            </button>
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="rounded-xl bg-blue-600 px-6 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60 transition"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>

        {error && <p role="alert" className="bg-rose-50 border-b border-rose-200 px-4 py-2 text-xs font-semibold text-rose-800">{error}</p>}

        {/* Canvas Body */}
        <div className="flex min-h-0 flex-1 relative">
          {/* Node Editor Drawer */}
          {selectedNode && (
            <NodeEditor
              node={selectedNode}
              onChange={changeNodeData}
              onClose={() => { setSelectedId(null); setNodes((nds) => nds.map((n) => ({ ...n, selected: false }))); }}
              onDuplicate={() => selectedId && onDuplicate(selectedId)}
            />
          )}

          {/* React Flow Canvas */}
          <div className="relative min-w-0 flex-1">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              defaultEdgeOptions={{ type: "smoothstep" }}
              onPaneClick={() => {
                setSelectedId(null);
                setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
                setAddMenuOpen(false);
              }}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={20} color="#cbd5e1" />
              <Controls showInteractive={false} className="!hidden" />
              
              {/* Minimap (Bottom Right) */}
              <MiniMap
                pannable
                zoomable
                className="!bottom-6 !right-6 !rounded-2xl !border !border-slate-200/90 !bg-white/90 !shadow-lg !overflow-hidden backdrop-blur-sm"
                nodeStrokeColor="#94a3b8"
                nodeColor={(n) => (n.id === selectedId ? "#3b82f6" : "#e2e8f0")}
              />

              {/* Floating Bottom Toolbar (Matching Reference Video Pill) */}
              <Panel position="bottom-center" className="!mb-6">
                <div className="relative flex items-center gap-1.5 rounded-2xl border border-slate-200/90 bg-white/95 p-1.5 shadow-xl backdrop-blur-sm ring-1 ring-black/5">
                  {/* Auto-Layout (Magic Wand) */}
                  <button
                    type="button"
                    onClick={autoLayout}
                    title="Auto-organize layout (Clean alignment)"
                    className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-600 text-white shadow-xs hover:bg-purple-700 transition"
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m19 11-8-8-8.5 8.5a2.12 2.12 0 0 0 0 3l5 5c.8.8 2.2.8 3 0Z"/><path d="m5 2 5 5"/><path d="M2 5l5 5"/><path d="m22 13-1.5 1.5"/><path d="m18 17-1.5 1.5"/></svg>
                  </button>

                  {/* Fit View */}
                  <button
                    type="button"
                    onClick={() => fitView({ duration: 300, padding: 0.2 })}
                    title="Fit view to canvas"
                    className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-600 hover:bg-slate-100 transition"
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
                  </button>

                  {/* Zoom Out */}
                  <button
                    type="button"
                    onClick={() => zoomOut({ duration: 200 })}
                    title="Zoom Out"
                    className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-600 hover:bg-slate-100 transition"
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </button>

                  {/* Zoom In */}
                  <button
                    type="button"
                    onClick={() => zoomIn({ duration: 200 })}
                    title="Zoom In"
                    className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-600 hover:bg-slate-100 transition"
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </button>

                  <div className="h-5 w-px bg-slate-200 mx-0.5" />

                  {/* Add Node Button with Type Selector */}
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setAddMenuOpen((v) => !v)}
                      className="flex h-9 items-center gap-1.5 rounded-xl bg-blue-600 px-4 text-xs font-bold text-white shadow-xs hover:bg-blue-700 transition"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                      <span>Node</span>
                    </button>

                    {addMenuOpen && (
                      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-56 rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl ring-1 ring-black/5 z-50">
                        <div className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100">
                          Add New Node
                        </div>
                        <div className="mt-1 space-y-0.5">
                          {MESSAGE_TYPES.map((t) => (
                            <button
                              key={t.value}
                              type="button"
                              onClick={() => addTypedNode(t.value)}
                              className="w-full flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition"
                            >
                              <span>
                                {t.value === "text" ? "💬" :
                                 t.value === "button" ? "🔘" :
                                 t.value === "list" ? "📋" :
                                 t.value === "condition" ? "🔀" :
                                 t.value === "delay" ? "⏱" :
                                 t.value === "template" ? "📑" :
                                 t.value === "get_user_data" ? "📥" : "📄"}
                              </span>
                              <span>{t.label}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
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

