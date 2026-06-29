import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ReactFlow, Controls, Background, MiniMap, Handle, Position,
  useNodesState, useEdgesState, useReactFlow, ReactFlowProvider,
  getBezierPath, EdgeLabelRenderer, BaseEdge, NodeProps, EdgeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import * as dagre from "@dagrejs/dagre";
import { api } from "../lib/api";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";
import { Network, Plus, Zap, Navigation2, X } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";

const inputStyle: React.CSSProperties = {
  background: "#eef5ee", border: "1px solid #d1e3d1", borderRadius: 12,
  padding: "9px 13px", fontSize: 14, color: "#0d1f10", width: "100%", outline: "none",
};

interface SupplierGraphData {
  nodes: { id: string; label: string; country: string; sector: string; esg_score: number; tco2e_30d: number; intensity: number; trend: "up" | "down" | "flat"; }[];
  edges: { id: string; source: string; target: string; transport_mode: string; weight_tonnes: number; }[];
}

const getFlag = (c: string) => { const f: Record<string, string> = { "USA": "🇺🇸", "US": "🇺🇸", "China": "🇨🇳", "India": "🇮🇳", "Germany": "🇩🇪", "Japan": "🇯🇵", "UK": "🇬🇧", "France": "🇫🇷" }; return f[c] || "🏳️"; };

const SupplierNode = ({ data, selected }: NodeProps) => {
  const d = data as any;
  const isHighInt = d.intensity >= 0.66;
  const isMedInt = d.intensity >= 0.33 && d.intensity < 0.66;
  
  // Style according to new Ecological Precision theme
  const bg = isHighInt ? "#2a1010" : isMedInt ? "#2a2210" : "#0d1a0f"; // very dark red/yellow/forest
  const border = selected ? "#6dc98a" : isHighInt ? "#dc2626" : isMedInt ? "#eab308" : "rgba(255,255,255,0.15)";
  const esgColor = d.esg_score < 40 ? "#dc2626" : d.esg_score <= 70 ? "#eab308" : "#22c55e";

  return (
    <div style={{ width: 180, background: bg, border: `1.5px solid ${border}`, borderRadius: 16, padding: 12, boxShadow: selected ? "0 0 0 2px rgba(109,201,138,0.3)" : "0 4px 12px rgba(0,0,0,0.1)", transition: "all 0.2s" }}>
      <Handle type="target" position={Position.Left} style={{ background: "#8ea58e", border: "none" }} />
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-sm truncate pr-2 text-white" title={d.label}>{d.label}</h3>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: esgColor, flexShrink: 0, marginTop: 4 }} title={`ESG: ${d.esg_score}`} />
      </div>
      <div className="flex items-center gap-2 text-xs mb-3 pb-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#8ea58e" }}>
        <span title={d.country}>{getFlag(d.country)}</span>
        <span className="truncate px-1.5 py-0.5 rounded" style={{ background: "rgba(255,255,255,0.06)" }}>{d.sector}</span>
      </div>
      <div className="flex justify-between items-center">
        <div className="font-bold text-white text-[13px]">{d.tco2e_30d} <span className="font-normal text-[10px]" style={{ color: "#8ea58e" }}>tCO2e</span></div>
        <div className="font-bold text-xs" style={{ color: d.trend === "up" ? "#dc2626" : d.trend === "down" ? "#22c55e" : "#8ea58e" }}>{d.trend === "up" ? "↑" : d.trend === "down" ? "↓" : "→"}</div>
      </div>
      <Handle type="source" position={Position.Right} style={{ background: "#8ea58e", border: "none" }} />
    </div>
  );
};

const SupplierEdge = ({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, markerEnd, style }: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const d = data as any;
  const icons: Record<string, string> = { air: "✈️", sea: "🚢", road: "🚛", rail: "🚆" };
  const icon = icons[d.transport_mode?.toLowerCase()] || "📦";
  
  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={{ ...style, strokeWidth: d.weight_tonnes > 1000 ? 2.5 : 1.5, stroke: "#3a9a65" }} />
      <EdgeLabelRenderer>
        <div style={{ position: 'absolute', transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`, pointerEvents: 'all', background: "#152218", border: "1px solid rgba(255,255,255,0.1)", color: "#c8dcc8" }}
             className="px-1.5 py-0.5 rounded text-[11px] flex items-center shadow-sm nodrag nopan">
          <span>{icon}</span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
};

const getLayoutedElements = (nodes: any[], edges: any[], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  const w = 200, h = 100;
  dagreGraph.setGraph({ rankdir: direction, nodesep: 80, ranksep: 120 });
  nodes.forEach(n => dagreGraph.setNode(n.id, { width: w, height: h }));
  edges.forEach(e => dagreGraph.setEdge(e.source, e.target));
  dagre.layout(dagreGraph);
  return { nodes: nodes.map(n => { const np = dagreGraph.node(n.id); return { ...n, targetPosition: Position.Left, sourcePosition: Position.Right, position: { x: np.x - w / 2, y: np.y - h / 2 } }; }), edges };
};

function SupplyChainMapInner() {
  const queryClient = useQueryClient();
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const { fitView } = useReactFlow();
  const [selectedSupplierId, setSelectedSupplierId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Add Edge Form State
  const [open, setOpen] = useState(false);
  const [fromSupplierId, setFromSupplierId] = useState("");
  const [toSupplierId, setToSupplierId] = useState("");
  const [transportMode, setTransportMode] = useState("road");
  const [distanceKm, setDistanceKm] = useState("1000");
  const [weightTonnes, setWeightTonnes] = useState("10");
  const [submitting, setSubmitting] = useState(false);

  const handleCreateEdge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fromSupplierId || !toSupplierId) return;
    if (fromSupplierId === toSupplierId) {
      alert("Source and target nodes must be different.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/supply-chain/edges", {
        from_supplier_id: fromSupplierId,
        to_supplier_id: toSupplierId,
        transport_mode: transportMode,
        distance_km: parseFloat(distanceKm),
        weight_tonnes: parseFloat(weightTonnes),
      });
      queryClient.invalidateQueries({ queryKey: ["supply-chain-graph"] });
      setOpen(false);
      setFromSupplierId("");
      setToSupplierId("");
      setTransportMode("road");
      setDistanceKm("1000");
      setWeightTonnes("10");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create edge.");
    } finally {
      setSubmitting(false);
    }
  };

  const { data: graphData } = useQuery<SupplierGraphData>({ queryKey: ["supply-chain-graph"], queryFn: async () => (await api.get("/supply-chain/graph")).data });

  useEffect(() => {
    if (graphData) {
      const initialNodes = graphData.nodes.map(n => ({ id: n.id, type: 'supplierNode', data: n, position: { x: 0, y: 0 } }));
      const initialEdges = graphData.edges.map(e => ({ id: e.id, source: e.source, target: e.target, type: 'supplierEdge', animated: true, data: { transport_mode: e.transport_mode, weight_tonnes: e.weight_tonnes } }));
      const layouted = getLayoutedElements(initialNodes, initialEdges);
      setNodes(layouted.nodes); setEdges(layouted.edges);
      setTimeout(() => fitView({ padding: 0.2 }), 100);
    }
  }, [graphData, setNodes, setEdges, fitView]);

  const onAutoLayout = useCallback(() => {
    const layouted = getLayoutedElements(nodes, edges);
    setNodes([...layouted.nodes]); setEdges([...layouted.edges]);
    setTimeout(() => fitView({ padding: 0.2, duration: 800 }), 50);
  }, [nodes, edges, setNodes, setEdges, fitView]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: any) => { setSelectedSupplierId(node.id); setDrawerOpen(true); }, []);
  const selectedNodeData = useMemo(() => nodes.find(n => n.id === selectedSupplierId)?.data as any, [nodes, selectedSupplierId]);

  const { data: sHist } = useQuery({ queryKey: ["hist", selectedSupplierId], queryFn: async () => [{ month: 'Jan', scope1: 120, scope2: 50, scope3: 300 }, { month: 'Feb', scope1: 110, scope2: 45, scope3: 290 }, { month: 'Mar', scope1: 115, scope2: 48, scope3: 310 }], enabled: !!selectedSupplierId && drawerOpen });
  const { data: sForc } = useQuery({ queryKey: ["forc", selectedSupplierId], queryFn: async () => [{ month: 'Apr', actual: 480, forecast: 480, lower: 470, upper: 490 }, { month: 'May', actual: null, forecast: 460, lower: 440, upper: 480 }, { month: 'Jun', actual: null, forecast: 440, lower: 410, upper: 470 }], enabled: !!selectedSupplierId && drawerOpen });

  const nodeTypes = useMemo(() => ({ supplierNode: SupplierNode }), []);
  const edgeTypes = useMemo(() => ({ supplierEdge: SupplierEdge }), []);

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] relative">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Network className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>Supply Chain Map</h1>
          <div className="px-3 py-1 rounded-full text-xs font-semibold" style={{ background: "#e8f2e8", color: "#5a6b5a", border: "1px solid #d1e3d1" }}>{nodes.length} Nodes · {edges.length} Edges</div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setOpen(true)} className="btn-ghost py-2 text-xs gap-1.5"><Plus className="h-3 w-3" /> Add Edge</button>
          <button className="btn-ghost py-2 text-xs gap-1.5" onClick={onAutoLayout}><Zap className="h-3 w-3" /> Auto Layout</button>
          <button className="btn-primary py-2 text-xs gap-1.5" onClick={() => fitView({ duration: 800 })}><Navigation2 className="h-3 w-3" /> Fit View</button>
        </div>
      </div>

      <div className="flex-1 rounded-[24px] overflow-hidden" style={{ background: "#0d1a0f", border: "1px solid #d1e3d1" }}>
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={onNodeClick} nodeTypes={nodeTypes} edgeTypes={edgeTypes} defaultEdgeOptions={{ type: 'supplierEdge', animated: true }} fitView minZoom={0.1}>
          <Background color="#ffffff" gap={20} size={1} style={{ opacity: 0.05 }} />
          <Controls style={{ display: 'flex', flexDirection: 'column', gap: 4 }} />
          <MiniMap nodeColor={(n: any) => n.data?.intensity >= 0.66 ? '#dc2626' : n.data?.intensity >= 0.33 ? '#eab308' : '#22c55e'} maskColor="rgba(13, 26, 15, 0.7)" style={{ background: "#152218", border: "1px solid rgba(255,255,255,0.1)" }} />
        </ReactFlow>
      </div>

      {drawerOpen && selectedNodeData && (
        <div className="absolute top-0 right-0 bottom-0 w-[400px] z-50 p-6 flex flex-col" style={{ background: "#0d1a0f", borderLeft: "1px solid rgba(255,255,255,0.1)", boxShadow: "-4px 0 20px rgba(0,0,0,0.2)" }}>
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-2 flex items-center gap-2">{selectedNodeData.label} <span>{getFlag(selectedNodeData.country)}</span></h2>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-black" style={{ background: selectedNodeData.esg_score >= 70 ? "#4ade80" : selectedNodeData.esg_score >= 40 ? "#facc15" : "#f87171" }}>ESG {selectedNodeData.esg_score}</span>
                <span className="text-[11px] text-[#8ea58e] uppercase font-semibold">{selectedNodeData.sector}</span>
              </div>
            </div>
            <button onClick={() => setDrawerOpen(false)} className="text-[#8ea58e] hover:text-white p-1 bg-white/5 rounded-lg"><X className="h-5 w-5" /></button>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-6 pr-2">
            <div className="space-y-3">
              <p className="text-xs font-semibold text-[#c8dcc8] uppercase tracking-wider">History (12m)</p>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sHist} margin={{ top: 0, left: -20, right: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" stroke="#5a7a5a" fontSize={10} />
                    <YAxis stroke="#5a7a5a" fontSize={10} />
                    <Tooltip contentStyle={{ background: "#152218", borderColor: "rgba(255,255,255,0.1)", borderRadius: 12, color: "#fff" }} />
                    <Area type="monotone" dataKey="scope1" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
                    <Area type="monotone" dataKey="scope2" stackId="1" stroke="#f97316" fill="#f97316" fillOpacity={0.4} />
                    <Area type="monotone" dataKey="scope3" stackId="1" stroke="#eab308" fill="#eab308" fillOpacity={0.4} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            <div className="space-y-3">
              <p className="text-xs font-semibold text-[#c8dcc8] uppercase tracking-wider">Forecast (6m)</p>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sForc} margin={{ top: 0, left: -20, right: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" stroke="#5a7a5a" fontSize={10} />
                    <YAxis stroke="#5a7a5a" fontSize={10} />
                    <Tooltip contentStyle={{ background: "#152218", borderColor: "rgba(255,255,255,0.1)", borderRadius: 12, color: "#fff" }} />
                    <Line type="monotone" dataKey="actual" stroke="#6dc98a" strokeWidth={2} dot={{ r: 3, fill: "#6dc98a" }} />
                    <Line type="monotone" dataKey="forecast" stroke="#6dc98a" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Edge Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent style={{ background: "#f5f8f5", border: "1px solid #d1e3d1", borderRadius: 20, maxWidth: 480 }}>
          <DialogHeader>
            <DialogTitle style={{ color: "#0d1f10" }}>Add Logistics Edge</DialogTitle>
            <DialogDescription style={{ color: "#5a6b5a" }}>
              Define a transport routing link between two nodes in your supply chain network.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateEdge} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="label-caps">From Node (Source)</label>
                <select 
                  value={fromSupplierId} 
                  onChange={(e) => setFromSupplierId(e.target.value)} 
                  style={inputStyle} 
                  required
                >
                  <option value="">Select source...</option>
                  {graphData?.nodes.map((n) => (
                    <option key={n.id} value={n.id}>{n.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label-caps">To Node (Destination)</label>
                <select 
                  value={toSupplierId} 
                  onChange={(e) => setToSupplierId(e.target.value)} 
                  style={inputStyle} 
                  required
                >
                  <option value="">Select destination...</option>
                  {graphData?.nodes.map((n) => (
                    <option key={n.id} value={n.id}>{n.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5 col-span-1">
                <label className="label-caps">Transit Mode</label>
                <select 
                  value={transportMode} 
                  onChange={(e) => setTransportMode(e.target.value)} 
                  style={inputStyle}
                >
                  <option value="road">🚛 Road</option>
                  <option value="sea">🚢 Sea</option>
                  <option value="air">✈️ Air</option>
                  <option value="rail">🚆 Rail</option>
                </select>
              </div>
              <div className="space-y-1.5 col-span-1">
                <label className="label-caps">Distance (km)</label>
                <input 
                  type="number" 
                  value={distanceKm} 
                  onChange={(e) => setDistanceKm(e.target.value)} 
                  style={inputStyle} 
                  required 
                  min="0"
                />
              </div>
              <div className="space-y-1.5 col-span-1">
                <label className="label-caps">Weight (tonnes)</label>
                <input 
                  type="number" 
                  value={weightTonnes} 
                  onChange={(e) => setWeightTonnes(e.target.value)} 
                  style={inputStyle} 
                  required 
                  min="0"
                />
              </div>
            </div>

            <DialogFooter className="gap-2 pt-2">
              <button type="button" onClick={() => setOpen(false)} className="btn-ghost text-sm py-2 px-5">Cancel</button>
              <button type="submit" disabled={submitting} className="btn-primary text-sm py-2 px-6">
                {submitting ? "Adding..." : "Add Link"}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function SupplyChainMap() {
  return <ReactFlowProvider><SupplyChainMapInner /></ReactFlowProvider>;
}
