import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Bot, Send, Plus, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Message { role: "user" | "assistant" | "system"; content: string; sources?: string[]; isFirstAssistant?: boolean; }
interface ConversationMeta { id: string; created_at: string; preview: string; }

const SUGGESTED = ["Which supplier has highest Scope 3 emissions?", "Am I on track to hit my target?", "How do I reduce air freight emissions?", "Generate a summary of last quarter"];

export default function Chat() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [convHistory, setConvHistory] = useState<ConversationMeta[]>([]);
  const [activeConvIdx, setActiveConvIdx] = useState<number | null>(null);

  useQuery<ConversationMeta[]>({
    queryKey: ["ai-conversations"],
    queryFn: async () => { const res = await api.get("/ai/conversations"); setConvHistory(res.data); return res.data; },
    retry: false,
  });

  const scrollToBottom = useCallback(() => { requestAnimationFrame(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }); }, []);
  useEffect(() => scrollToBottom(), [messages, isLoading, scrollToBottom]);
  useEffect(() => { if (textareaRef.current) { textareaRef.current.style.height = "auto"; textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`; } }, [input]);

  useEffect(() => {
    if (activeConvIdx !== null && convHistory[activeConvIdx]) {
      const selected = convHistory[activeConvIdx] as any;
      setMessages(selected.messages || []);
    }
  }, [activeConvIdx, convHistory]);

  const handleSend = async (msg?: string) => {
    const text = (msg ?? input).trim();
    if (!text || isLoading) return;
    setInput("");
    setMessages(p => [...p, { role: "user", content: text }]);
    setIsLoading(true);
    try {
      const res = await api.post("/ai/conversations", { message: text, conversation_id: conversationId });
      const data = res.data;
      const newConvId = data.id ?? data.conversation_id ?? conversationId;
      setConversationId(newConvId);
      setMessages(data.messages || []);
      if (newConvId) {
        setConvHistory(p => {
          const existing = p.find(c => c.id === newConvId);
          if (existing) {
            return p.map(c => c.id === newConvId ? { ...c, preview: text, messages: data.messages } : c);
          } else {
            return [{ id: newConvId, created_at: new Date().toISOString(), preview: text, messages: data.messages } as any, ...p];
          }
        });
        if (!conversationId) {
          setActiveConvIdx(0);
        }
      }
    } catch (err: any) {
      setMessages(p => [...p, { role: "system", content: `⚠️ ${err.response?.data?.detail || "An error occurred."}` }]);
    } finally { setIsLoading(false); }
  };

  return (
    <div className="flex h-[calc(100vh-100px)] rounded-[24px] overflow-hidden" style={{ border: "1px solid #d1e3d1", background: "#f5f8f5", boxShadow: "0 4px 20px rgba(13,26,15,0.05)" }}>
      {/* Sidebar */}
      <div className="w-[280px] shrink-0 flex flex-col" style={{ background: "#e8f2e8", borderRight: "1px solid #d1e3d1" }}>
        <div className="p-4 border-b" style={{ borderColor: "#d1e3d1" }}>
          <button onClick={() => { setMessages([]); setConversationId(null); setActiveConvIdx(null); }} className="w-full btn-primary py-2.5 text-sm gap-2">
            <Plus className="h-4 w-4" /> New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {convHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <MessageSquare style={{ width: 20, height: 20, color: "#8a9b8a", marginBottom: 8 }} />
              <p className="text-xs" style={{ color: "#5a6b5a" }}>No conversations yet</p>
            </div>
          ) : (
            convHistory.map((conv, idx) => (
              <button key={conv.id} onClick={() => { setActiveConvIdx(idx); setConversationId(conv.id); }}
                className="w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors"
                style={{ background: activeConvIdx === idx ? "rgba(45,122,79,0.12)" : "transparent", color: activeConvIdx === idx ? "#1f5e3a" : "#2d3d2d" }}
              >
                <p className="font-semibold truncate leading-tight">{conv.preview}</p>
                <p className="text-[10px] mt-1 opacity-70">{new Date(conv.created_at).toLocaleDateString()}</p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat */}
      <div className="flex flex-1 flex-col min-w-0" style={{ background: "#fcfdfc" }}>
        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: "#d1e3d1" }}>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl" style={{ background: "linear-gradient(135deg,#2d7a4f,#3a9a65)" }}>
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-bold" style={{ color: "#0d1f10" }}>CarbonLens AI</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] uppercase font-semibold tracking-wider" style={{ color: "#2d7a4f" }}>Online</span>
              </div>
            </div>
          </div>
          <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full" style={{ background: "#eef5ee", color: "#5a6b5a", border: "1px solid #d1e3d1" }}>Powered by Groq LLaMA 3.1</span>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto text-center animate-fade-in-up">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl mb-5" style={{ background: "rgba(45,122,79,0.12)" }}>
                <Bot style={{ width: 32, height: 32, color: "#2d7a4f" }} />
              </div>
              <h3 className="text-xl font-bold mb-2" style={{ color: "#0d1f10", letterSpacing: "-0.01em" }}>How can I help you today?</h3>
              <p className="text-sm mb-8" style={{ color: "#5a6b5a" }}>Analyze data, optimize supply chains, or track sustainability goals.</p>
              <div className="grid grid-cols-1 gap-2.5 w-full">
                {SUGGESTED.map(p => (
                  <button key={p} onClick={() => handleSend(p)} disabled={isLoading} className="text-left text-sm px-4 py-3 rounded-xl transition-colors" style={{ background: "#eef5ee", border: "1px solid #d1e3d1", color: "#2d3d2d" }} onMouseEnter={e => e.currentTarget.style.borderColor = "#2d7a4f"} onMouseLeave={e => e.currentTarget.style.borderColor = "#d1e3d1"}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              if (msg.role === "system") return <div key={idx} className="flex justify-center"><span className="text-xs px-3 py-1.5 rounded-full bg-red-100 text-red-600 border border-red-200">{msg.content}</span></div>;
              const isUser = msg.role === "user";
              return (
                <div key={idx} className={`flex items-end gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
                  {!isUser && (
                    <div className="flex h-8 w-8 items-center justify-center rounded-full shrink-0 mb-1" style={{ background: "rgba(45,122,79,0.15)" }}>
                      <Bot style={{ width: 16, height: 16, color: "#2d7a4f" }} />
                    </div>
                  )}
                  <div className={`max-w-[75%] space-y-1 ${isUser ? "items-end" : "items-start"}`}>
                    <div className={`px-5 py-3.5 text-[15px] leading-relaxed shadow-sm`} style={{
                      borderRadius: 20, borderBottomRightRadius: isUser ? 4 : 20, borderBottomLeftRadius: isUser ? 20 : 4,
                      background: isUser ? "#2d7a4f" : "#fff", color: isUser ? "#fff" : "#0d1f10", border: isUser ? "none" : "1px solid #d1e3d1"
                    }}>
                      {isUser ? msg.content : (
                        <ReactMarkdown components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-2 pl-2">{children}</ul>,
                          li: ({ children }) => <li>{children}</li>,
                          strong: ({ children }) => <strong className="font-semibold text-black">{children}</strong>,
                          code: ({ children }) => <code className="bg-gray-100 text-green-800 px-1.5 py-0.5 rounded text-[13px] font-mono">{children}</code>
                        }}>
                          {msg.content}
                        </ReactMarkdown>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
          {isLoading && (
             <div className="flex items-end gap-3">
               <div className="flex h-8 w-8 items-center justify-center rounded-full shrink-0 mb-1" style={{ background: "rgba(45,122,79,0.15)" }}>
                 <Bot style={{ width: 16, height: 16, color: "#2d7a4f" }} />
               </div>
               <div className="px-5 py-4 bg-white border rounded-2xl rounded-bl-sm" style={{ borderColor: "#d1e3d1" }}>
                 <div className="flex gap-1.5">
                   {[0,1,2].map(i => <div key={i} className="h-2 w-2 rounded-full bg-green-300 animate-bounce" style={{ animationDelay: `${i*0.15}s` }} />)}
                 </div>
               </div>
             </div>
          )}
        </div>

        <div className="p-4" style={{ background: "#fcfdfc", borderTop: "1px solid #d1e3d1" }}>
          <div className="flex items-end gap-3 px-4 py-3 rounded-[20px] transition-colors" style={{ background: "#e8f2e8", border: "1px solid #d1e3d1" }}>
            <textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              disabled={isLoading} placeholder="Message CarbonLens AI..." rows={1}
              className="flex-1 resize-none bg-transparent text-[15px] outline-none max-h-[120px]" style={{ color: "#0d1f10" }}
            />
            <button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="flex items-center justify-center shrink-0 h-9 w-9 rounded-full transition-all" style={{ background: input.trim() && !isLoading ? "#2d7a4f" : "#b8d0b8", color: "#fff" }}>
              <Send className="h-4 w-4 ml-0.5" />
            </button>
          </div>
          <p className="text-[10px] text-center mt-2 font-medium" style={{ color: "#8a9b8a" }}>AI can make mistakes. Verify important emission calculations.</p>
        </div>
      </div>
    </div>
  );
}
