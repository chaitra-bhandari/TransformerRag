import { useState, useRef, useEffect } from "react";


// ── Tokens ────────────────────────────────────────────────────────
const T = {
  bg:"#0D0F14", sidebar:"#08090D", surface:"#131720",
  elevated:"#1A1E2A", border:"#1E2436",
  accent:"#F59E0B", accentDim:"rgba(245,158,11,0.10)", accentBorder:"rgba(245,158,11,0.22)",
  blue:"#3B82F6", green:"#10B981", red:"#EF4444", purple:"#8B5CF6", cyan:"#06B6D4",
  textPrimary:"#EDF2FF", textSecondary:"#7A8AAE", textMuted:"#364058",
  userBubble:"#1C2238",
};

// ── Mock SQLite + Blob data ───────────────────────────────────────
// Each project has its own vector index namespace and its own blob containers.
// Old projects already have Order A/B files in their output blob container.
const SQLITE_PROJECTS = [
  {
    id:"p1", name:"NORD-STREAM-7",    type:"both",     files:14, lastUpdated:"2026-02-12",
    // Orders already generated — stored in output-p1 blob container
    orders: { a: "NORD-STREAM-7_Order_A.docx", b: "NORD-STREAM-7_Order_B.docx" },
  },
  {
    id:"p2", name:"DELTA-OFFSHORE-3", type:"offshore", files:8,  lastUpdated:"2026-02-10",
    orders: { a: null, b: "DELTA-OFFSHORE-3_Order_B.docx" }, // only B exists
  },
  {
    id:"p3", name:"ALPINE-GRID-2024", type:"onshore",  files:11, lastUpdated:"2026-02-08",
    orders: { a: "ALPINE-GRID-2024_Order_A.docx", b: null }, // only A exists
  },
  {
    id:"p4", name:"BALTIC-CONNECT-2", type:"both",     files:6,  lastUpdated:"2026-01-30",
    orders: { a: null, b: null }, // indexed but no orders yet
  },
];

const PIPELINE_STAGES = [
  { id:"upload", label:"Upload to Blob",        icon:"☁"  },
  { id:"di",     label:"Document Intelligence", icon:"⬡"  },
  { id:"di_out", label:"DI Output → Container", icon:"◈"  },
  { id:"chunk",  label:"Chunk + Tag Metadata",  icon:"◎"  },
  { id:"vector", label:"Vector Index",          icon:"◐"  },
  { id:"rag",    label:"RAG Verified",          icon:"✦"  },
];

const ORDER_STEPS = [
  "Querying project vector index…",
  "Building LLM prompt with chunks…",
  "LLM generating structured JSON…",
  "Parsing & validating output…",
  "Filling DOCX template…",
  "Saving to output blob container…",
];

const HISTORY = [
  { id:"h1", title:"NORD-STREAM-7 · Order A+B",    date:"Today",     icon:"📋" },
  { id:"h2", title:"DELTA-OFFSHORE-3 · Query",     date:"Yesterday", icon:"💬" },
  { id:"h3", title:"ALPINE-GRID · Order A",        date:"Feb 10",    icon:"📋" },
];

// ── Mock RAG — scoped to project_id + scope filter in vector DB ──
const mockRagAnswer = (q, project, scope = "project") => {
  const lo = q.toLowerCase();
  const scopeLabel = scope === "project" ? "all scopes" : scope;
  const scopeNote  = `\n\n_Results filtered to: **${project.name}** · scope: **${scopeLabel}** · ${project.files} chunks searched_`;

  if(lo.includes("cost")||lo.includes("price")||lo.includes("budget"))
    return `The **${project.name}** (${scopeLabel}) cost breakdown shows a total estimated value of **€${(Math.random()*5+2).toFixed(1)}M**. Key line items from the indexed documents include mobilisation (€320K), materials procurement (€2.1M), and installation works (€1.6M). See Annex B, Section 4.1 of the project specification.${scopeNote}`;
  if(lo.includes("scope")||lo.includes("work")||lo.includes("deliverable"))
    return `The scope of work for **${project.name}** (${scopeLabel}) covers ${scope==="offshore"?"subsea and offshore activities including ROV inspection, subsea tie-in works, and marine operations":scope==="onshore"?"land-based activities including pipeline installation, hydrostatic testing, coating inspection, and commissioning":"both onshore and offshore activities"}. Refer to Technical Specification Rev.3, Clause 7.2–7.8.${scopeNote}`;
  if(lo.includes("deadline")||lo.includes("schedule")||lo.includes("timeline"))
    return `The ${scopeLabel} schedule for **${project.name}** shows planned completion by **Q3 2026**. Critical path: ${scope==="offshore"?"subsea tie-in (15 days float), ROV survey (8 days float)":scope==="onshore"?"hydrostatic testing (10 days float), commissioning (12 days float)":"subsea tie-in (15 days float) and FAT testing (8 days float)"}. See P6 baseline schedule in Annex C.${scopeNote}`;
  return `Based on the indexed documents for **${project.name}** (scope: ${scopeLabel}), the relevant sections are found in clauses 7.3 and Annex B. The documents reference ISO 13623 compliance and project-specific deviations in variation order VO-${Math.floor(Math.random()*20)+1} dated Jan 2026.${scopeNote}`;
};

// ── Helpers ───────────────────────────────────────────────────────
const delay = (ms) => new Promise(r => setTimeout(r, ms));
const uid   = () => Math.random().toString(36).slice(2, 9);

// ── Atoms ─────────────────────────────────────────────────────────
const TypeTag = ({ type }) => {
  const m = {
    both:    { label:"Onshore + Offshore", color:T.green,  bg:"rgba(16,185,129,0.1)"  },
    onshore: { label:"Onshore",            color:T.blue,   bg:"rgba(59,130,246,0.1)"  },
    offshore:{ label:"Offshore",           color:T.purple, bg:"rgba(139,92,246,0.1)"  },
  }[type]||{ label:type, color:T.textMuted, bg:T.elevated };
  return <span style={{ display:"inline-flex",alignItems:"center",padding:"2px 7px",borderRadius:4,background:m.bg,color:m.color,fontSize:10,fontWeight:700,border:`1px solid ${m.color}25`,fontFamily:"monospace" }}>{m.label}</span>;
};

const Spin = ({ size=13, color=T.accent }) => (
  <div style={{ width:size,height:size,border:`1.5px solid transparent`,borderTopColor:color,borderRadius:"50%",animation:"spin .65s linear infinite",flexShrink:0 }}/>
);

const TypingDots = () => (
  <div style={{ display:"flex",gap:4,padding:"4px 0" }}>
    {[0,1,2].map(i=><div key={i} style={{ width:7,height:7,borderRadius:"50%",background:T.textMuted,animation:`pdot 1.2s ease ${i*.2}s infinite` }}/>)}
  </div>
);

const RichText = ({ text }) => (
  <span dangerouslySetInnerHTML={{ __html: text
    .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
    .replace(/\n/g,"<br/>") }}/>
);

const DoneBadge = ({ label, color=T.accent }) => (
  <div style={{ marginTop:10,padding:"8px 13px",background:T.accentDim,borderRadius:7,border:`1px solid ${T.accentBorder}`,fontSize:13,display:"inline-flex",alignItems:"center",gap:8,color }}>
    <span>✓</span><span>{label}</span>
  </div>
);

// ── CSS ───────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&family=Geist:wght@300;400;500;600;700&display=swap');
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{background:${T.bg};color:${T.textPrimary};font-family:'Geist',sans-serif;font-size:14px}
  ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:${T.border};border-radius:2px}
  .mono{font-family:'Geist Mono',monospace}

  @keyframes spin  {to{transform:rotate(360deg)}}
  @keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  @keyframes blink {0%,100%{opacity:1}50%{opacity:0}}
  @keyframes pdot  {0%,100%{opacity:.35;transform:scale(.8)}50%{opacity:1;transform:scale(1)}}
  @keyframes pglow {0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.3)}50%{box-shadow:0 0 0 5px rgba(245,158,11,0)}}

  .msg{animation:fadeUp .2s ease forwards}

  .main-btn{border:1px solid ${T.border};border-radius:12px;padding:20px 22px;cursor:pointer;background:${T.surface};transition:all .18s;text-align:left;font-family:'Geist',sans-serif;width:100%}
  .main-btn:hover{border-color:${T.accent};background:${T.accentDim};transform:translateY(-1px)}

  .sub-btn{border:1px solid ${T.border};border-radius:9px;padding:12px 15px;cursor:pointer;background:${T.elevated};transition:all .15s;text-align:left;font-family:'Geist',sans-serif;width:100%;display:flex;align-items:center;gap:12px}
  .sub-btn:hover{border-color:${T.accent};background:${T.accentDim}}

  .order-btn{flex:1;border-radius:9px;padding:14px 10px;cursor:pointer;border:1px solid ${T.border};background:${T.elevated};font-family:'Geist',sans-serif;transition:all .15s;display:flex;flex-direction:column;align-items:center;gap:5px}
  .order-btn:hover{border-color:${T.accent};background:${T.accentDim}}

  .chip{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid ${T.border};background:${T.elevated};color:${T.textSecondary};transition:all .15s;white-space:nowrap;font-family:'Geist',sans-serif}
  .chip:hover{border-color:${T.accent};color:${T.accent};background:${T.accentDim}}

  .sb-item{padding:7px 10px;border-radius:6px;cursor:pointer;color:${T.textSecondary};font-size:13px;transition:all .12s;border:1px solid transparent;display:flex;align-items:flex-start;gap:8px}
  .sb-item:hover{background:${T.surface};color:${T.textPrimary};border-color:${T.border}}

  .input-wrap{background:${T.elevated};border:1px solid ${T.border};border-radius:13px;transition:border-color .2s,box-shadow .2s}
  .input-wrap:focus-within{border-color:${T.accent};box-shadow:0 0 0 3px rgba(245,158,11,.07)}

  textarea{background:transparent;border:none;outline:none;resize:none;color:${T.textPrimary};font-family:'Geist',sans-serif;font-size:14px;width:100%;line-height:1.65}
  textarea::placeholder{color:${T.textMuted}}

  .txt-input{background:${T.surface};border:1.5px solid ${T.border};border-radius:8px;color:${T.textPrimary};font-family:'Geist Mono',monospace;font-size:14px;padding:10px 14px;outline:none;width:100%;transition:border-color .2s,box-shadow .2s;letter-spacing:.4px}
  .txt-input:focus{border-color:${T.accent};box-shadow:0 0 0 3px rgba(245,158,11,.07)}
  .txt-input::placeholder{color:${T.textMuted};font-family:'Geist',sans-serif;letter-spacing:0}

  select{background:${T.surface};border:1px solid ${T.border};border-radius:5px;color:${T.textPrimary};font-family:'Geist',sans-serif;font-size:12px;padding:5px 9px;outline:none;cursor:pointer;appearance:none}
  select:focus{border-color:${T.accent}}

  .send-btn{width:34px;height:34px;border-radius:8px;border:none;cursor:pointer;background:${T.accent};color:#000;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;transition:all .15s;flex-shrink:0}
  .send-btn:hover{filter:brightness(1.1)}.send-btn:disabled{opacity:.28;cursor:not-allowed;filter:none}

  .drop-zone{border:1.5px dashed ${T.border};border-radius:8px;padding:22px;text-align:center;cursor:pointer;transition:all .15s;margin-bottom:10px}
  .drop-zone:hover,.drop-zone.drag{border-color:${T.accent};background:${T.accentDim}}

  .si{width:26px;height:26px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
  .si-done  {background:rgba(16,185,129,.12);color:${T.green};border:1px solid rgba(16,185,129,.28)}
  .si-active{background:${T.accentDim};color:${T.accent};border:1px solid ${T.accentBorder};animation:pglow 2s infinite}
  .si-idle  {background:${T.surface};color:${T.textMuted};border:1px solid ${T.border}}

  .rag-card{background:${T.surface};border:1px solid rgba(6,182,212,0.25);border-radius:10px;padding:18px;margin-top:10px;position:relative;overflow:hidden}
  .rag-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,${T.cyan},transparent)}
  .scope-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:4px;background:rgba(6,182,212,0.1);border:1px solid rgba(6,182,212,0.22);color:${T.cyan};font-size:11px;font-weight:600}

  .order-exists{background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:8px;padding:10px 14px}
  .order-missing{background:rgba(245,158,11,0.07);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:10px 14px}
`;

// ── Bubble ────────────────────────────────────────────────────────
const Bubble = ({ role, children, streaming }) => {
  const isUser = role === "user";
  return (
    <div className="msg" style={{ display:"flex",gap:12,alignItems:"flex-start",flexDirection:isUser?"row-reverse":"row" }}>
      <div style={{ width:30,height:30,borderRadius:isUser?"50%":"8px",flexShrink:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:isUser?11:14,fontWeight:700,
        background:isUser?T.userBubble:T.accentDim,border:`1px solid ${isUser?T.border:T.accentBorder}`,color:isUser?T.textSecondary:T.accent }}>
        {isUser?"U":"D"}
      </div>
      <div style={{ maxWidth:"80%",background:isUser?T.userBubble:"transparent",border:isUser?`1px solid ${T.border}`:"none",
        borderRadius:isUser?"12px 4px 12px 12px":0,padding:isUser?"10px 14px":"2px 0",lineHeight:1.7,color:T.textPrimary,fontSize:14 }}>
        {children}
        {streaming&&<span style={{ animation:"blink 1s infinite",color:T.accent }}>▌</span>}
      </div>
    </div>
  );
};

const Chips = ({ items, onPick }) => (
  <div style={{ display:"flex",gap:7,flexWrap:"wrap",marginTop:12 }}>
    {items.map(s=><button key={s} className="chip" onClick={()=>onPick(s)}>{s}</button>)}
  </div>
);

// ══════════════════════════════════════════════════════════════════
// WIDGETS
// ══════════════════════════════════════════════════════════════════

// ── Home ──────────────────────────────────────────────────────────
const HomeWidget = ({ onPick }) => (
  <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginTop:14,maxWidth:500 }}>
    {[
      { key:"generate", icon:"📋", label:"Generate Orders",  desc:"Produce Order A / Order B from your documents",   color:T.accent },
      { key:"query",    icon:"💬", label:"Query Documents",  desc:"Ask questions — answered from your project only", color:T.cyan  },
    ].map(o=>(
      <button key={o.key} className="main-btn" onClick={()=>onPick(o.key)}>
        <div style={{ fontSize:28,marginBottom:10 }}>{o.icon}</div>
        <div style={{ fontWeight:700,fontSize:15,marginBottom:5,color:o.color }}>{o.label}</div>
        <div style={{ fontSize:12,color:T.textSecondary,lineHeight:1.5 }}>{o.desc}</div>
      </button>
    ))}
  </div>
);

// ── Generate: New or Old ──────────────────────────────────────────
const NewOrOldWidget = ({ onPick }) => (
  <div style={{ display:"flex",flexDirection:"column",gap:9,marginTop:12,maxWidth:440 }}>
    {[
      { key:"new", icon:"✦", label:"New Project",      desc:"Upload files → DI pipeline → generate order",          color:T.accent },
      { key:"old", icon:"◈", label:"Existing Project", desc:"Search by project name → find Order A / B → download",  color:T.blue  },
    ].map(o=>(
      <button key={o.key} className="sub-btn" onClick={()=>onPick(o.key)}>
        <div style={{ width:38,height:38,borderRadius:9,flexShrink:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,
          background:`${o.color}14`,border:`1px solid ${o.color}30`,color:o.color }}>{o.icon}</div>
        <div>
          <div style={{ fontWeight:700,fontSize:14,color:o.color,marginBottom:3 }}>{o.label}</div>
          <div style={{ fontSize:12,color:T.textSecondary }}>{o.desc}</div>
        </div>
      </button>
    ))}
  </div>
);

// ── Project name search (shared by Old Project + Query) ───────────
const ProjectSearch = ({ label, hint, accentColor=T.accent, onSelect }) => {
  const [val,setVal]       = useState("");
  const [matches,setMatches] = useState([]);
  const [status,setStatus] = useState("idle"); // idle|searching|found|notfound
  const ref = useRef();
  useEffect(()=>{ ref.current?.focus(); },[]);

  const search = async (v) => {
    const q = v.trim().toUpperCase();
    setVal(v.toUpperCase());
    if(q.length < 2){ setMatches([]); setStatus("idle"); return; }
    setStatus("searching");
    await delay(380);
    const found = SQLITE_PROJECTS.filter(p=>p.name.includes(q));
    setMatches(found);
    setStatus(found.length > 0 ? "found" : "notfound");
  };

  return (
    <div style={{ marginTop:12,maxWidth:480 }}>
      <label style={{ display:"block",fontSize:11,color:T.textMuted,marginBottom:7,textTransform:"uppercase",letterSpacing:"1px",fontWeight:600 }}>
        {label} <span style={{ color:T.textMuted,textTransform:"none",letterSpacing:0,fontWeight:400 }}>{hint}</span>
      </label>
      <div style={{ position:"relative",marginBottom:10 }}>
        <input className="txt-input" ref={ref} placeholder="e.g. NORD-STREAM-7" value={val}
          onChange={e=>search(e.target.value)} />
        {status==="searching" && (
          <div style={{ position:"absolute",right:12,top:"50%",transform:"translateY(-50%)" }}><Spin size={14}/></div>
        )}
      </div>

      {matches.length > 0 && (
        <div style={{ display:"flex",flexDirection:"column",gap:6 }}>
          {matches.map(p=>(
            <button key={p.id} className="sub-btn" onClick={()=>onSelect(p)}>
              <div style={{ width:36,height:36,borderRadius:8,flexShrink:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,fontWeight:700,
                background:`${accentColor}14`,border:`1px solid ${accentColor}30`,color:accentColor }}>{p.name[0]}</div>
              <div style={{ flex:1,minWidth:0 }}>
                <div style={{ fontWeight:700,fontSize:13,marginBottom:3 }} className="mono">{p.name}</div>
                <div style={{ display:"flex",gap:7,alignItems:"center",flexWrap:"wrap" }}>
                  <TypeTag type={p.type}/>
                  <span style={{ fontSize:11,color:T.green }}>✓ {p.files} files indexed</span>
                  <span style={{ fontSize:10,color:T.textMuted }}>Updated {p.lastUpdated}</span>
                </div>
              </div>
              <span style={{ fontSize:11,color:T.textMuted,flexShrink:0 }}>Select →</span>
            </button>
          ))}
        </div>
      )}

      {status==="notfound" && (
        <div style={{ padding:"10px 14px",background:"rgba(239,68,68,0.08)",borderRadius:8,border:`1px solid rgba(239,68,68,0.2)`,fontSize:13,color:T.red }}>
          ⚠ No indexed project found for "<strong>{val}</strong>". Check the name or create a new project.
        </div>
      )}
    </div>
  );
};

// ── Old project: show Order A + Order B status from blob ──────────
const OldProjectOrders = ({ project, onGenerate, onDownload }) => {
  const [downloading, setDownloading] = useState({});
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Fetch real orders from backend on mount
  useEffect(() => {
    const fetchOrders = async () => {
      try {
        setLoading(true);        const response = await fetch(`/api/projects/${project.name}`, {
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
          const data = await response.json();
          setOrders([
            { key:"a", label:"Order A", icon:"📄", color:T.blue,   filename:data.orders?.order_a },
            { key:"b", label:"Order B", icon:"📋", color:T.purple, filename:data.orders?.order_b },
          ]);
        } else {
          // Fallback to project.orders if API fails
          setOrders([
            { key:"a", label:"Order A", icon:"📄", color:T.blue,   filename:project.orders.a },
            { key:"b", label:"Order B", icon:"📋", color:T.purple, filename:project.orders.b },
          ]);
        }
      } catch (error) {
        console.error('Failed to fetch orders:', error);
        // Fallback to project.orders
        setOrders([
          { key:"a", label:"Order A", icon:"📄", color:T.blue,   filename:project.orders.a },
          { key:"b", label:"Order B", icon:"📋", color:T.purple, filename:project.orders.b },
        ]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchOrders();
  }, [project.name]);
  
  const downloadFile = async (filename) => {
    try {
      setDownloading(p => ({...p, [filename]: true}));      
      // Construct full blob path
      const projectName = ctx.project?.name || ctx.queryProject?.name || "";
      const fullPath = projectName ? `${projectName}/${filename}` : filename;
      const encodedBlob = encodeURIComponent(fullPath);
      
      console.log(` Downloading: ${fullPath}`);  // Debug log
      
      const response = await fetch(`/api/orders/download?blob=${encodedBlob}`, {
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        console.error(` Download failed: ${response.status} ${response.statusText}`);
        throw new Error(`Download failed: ${response.statusText}`);
      }
      
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition') || '';
      let downloadName = filename.split('/').pop() || 'order.docx';
      
      if (contentDisposition) {
        // Try to match RFC 2184 format: filename*=UTF-8''encoded_name
        let match = contentDisposition.match(/filename\*=UTF-8''(.+?)(?:;|$)/);
        if (match) {
          try {
            // Decode URL-encoded filename
            downloadName = decodeURIComponent(match[1]);
            console.log(` Using RFC 2184 filename: ${downloadName}`);
          } catch (e) {
            console.warn('Failed to decode RFC 2184 filename, trying fallback');
          }
        }
        
        // Fallback: Try simple filename="..."
        if (!match || downloadName === filename.split('/').pop()) {
          match = contentDisposition.match(/filename="([^"]+)"/);
          if (match) downloadName = match[1];
        }
      }
      
      console.log(` Received file: ${downloadName}`);
      
      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      console.log(`Download complete: ${downloadName}`);
      
    } catch (error) {
      console.error(' Download error:', error);
      alert(`Download failed: ${error.message}`);
    } finally {
      setDownloading(p => ({...p, [filename]: false}));
    }
  };
  
  if (loading) {
    return (
      <div style={{ marginTop:12,maxWidth:480,padding:"20px",textAlign:"center",color:T.textMuted }}>
         Loading orders...
      </div>
    );
  }
  
  return (
    <div style={{ marginTop:12,maxWidth:480 }}>
      {/* Project header */}
      <div style={{ display:"flex",alignItems:"center",gap:10,padding:"11px 14px",background:T.elevated,borderRadius:9,border:`1px solid ${T.border}`,marginBottom:14 }}>
        <div style={{ width:36,height:36,borderRadius:8,background:T.accentDim,border:`1px solid ${T.accentBorder}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,color:T.accent,fontWeight:700,flexShrink:0 }}>
          {project.name[0]}
        </div>
        <div style={{ flex:1,minWidth:0 }}>
          <div style={{ fontWeight:700,fontSize:14 }} className="mono">{project.name}</div>
          <div style={{ display:"flex",gap:7,alignItems:"center",marginTop:3 }}>
            <TypeTag type={project.type}/>
            <span style={{ fontSize:11,color:T.green }}>✓ {project.files} files in Blob</span>
          </div>
        </div>
        <div style={{ fontSize:10,color:T.textMuted,textAlign:"right",lineHeight:1.6 }}>
          <div>SQLite ✓</div>
          <div>Blob ✓</div>
        </div>
      </div>

      <div style={{ fontSize:11,color:T.textMuted,fontWeight:700,textTransform:"uppercase",letterSpacing:"1px",marginBottom:10 }}>
        Orders in output container:
      </div>

      <div style={{ display:"flex",flexDirection:"column",gap:8 }}>
        {orders.map(o=>(
          <div key={o.key} className={o.filename?"order-exists":"order-missing"}>
            <div style={{ display:"flex",alignItems:"center",justifyContent:"space-between" }}>
              <div style={{ display:"flex",alignItems:"center",gap:10 }}>
                <span style={{ fontSize:22 }}>{o.icon}</span>
                <div>
                  <div style={{ fontWeight:700,fontSize:14,color:o.filename?T.textPrimary:T.textSecondary }}>{o.label}</div>
                  <div style={{ fontSize:11,marginTop:2 }} className="mono">
                    {o.filename
                      ? <span style={{ color:T.green }}>✓ {o.filename}</span>
                      : <span style={{ color:T.accent }}>Not generated yet</span>}
                  </div>
                </div>
              </div>
              {o.filename
                ? (
                  <button onClick={()=>downloadFile(o.filename)} disabled={downloading[o.filename]}
                    style={{ padding:"7px 16px",borderRadius:7,border:"none",cursor:downloading[o.filename]?"wait":"pointer",fontFamily:"'Geist',sans-serif",fontWeight:600,fontSize:12,background:o.color,color:"#fff",opacity:downloading[o.filename]?0.7:1 }}>
                    {downloading[o.filename] ? "⏳ Downloading..." : "⬇ Download"}
                  </button>
                )
                : (
                  <button onClick={()=>onGenerate(o.key, project)}
                    style={{ padding:"7px 16px",borderRadius:7,fontFamily:"'Geist',sans-serif",fontWeight:600,fontSize:12,cursor:"pointer",
                      background:"transparent",color:T.accent,border:`1px solid ${T.accentBorder}` }}>
                    ⚡ Generate
                  </button>
                )
              }
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ── New project form ──────────────────────────────────────────────
const NewProjectForm = ({ onConfirm }) => {
  const [name,setName] = useState("");
  const [type,setType] = useState("both");
  const ref = useRef();
  useEffect(()=>{ ref.current?.focus(); },[]);
  return (
    <div style={{ background:T.surface,border:`1px solid ${T.accentBorder}`,borderRadius:11,padding:18,marginTop:12,maxWidth:480,position:"relative",overflow:"hidden" }}>
      <div style={{ position:"absolute",top:0,left:0,right:0,height:2,background:`linear-gradient(90deg,${T.accent},transparent)` }}/>
      <div style={{ fontSize:11,fontWeight:700,color:T.accent,textTransform:"uppercase",letterSpacing:"1px",marginBottom:14 }}>✦ New Project</div>
      <div style={{ marginBottom:12 }}>
        <label style={{ display:"block",fontSize:11,color:T.textMuted,marginBottom:6,textTransform:"uppercase",letterSpacing:"1px",fontWeight:600 }}>Project Name</label>
        <input ref={ref} className="txt-input" placeholder="e.g. NORD-STREAM-8" value={name}
          onChange={e=>setName(e.target.value.toUpperCase())}
          onKeyDown={e=>e.key==="Enter"&&name.trim()&&onConfirm({name,type})} />
      </div>
      <div style={{ marginBottom:16 }}>
        <label style={{ display:"block",fontSize:11,color:T.textMuted,marginBottom:8,textTransform:"uppercase",letterSpacing:"1px",fontWeight:600 }}>Project Type</label>
        <div style={{ display:"flex",gap:8 }}>
          {[{v:"both",l:"Onshore + Offshore",c:T.green},{v:"onshore",l:"Onshore",c:T.blue},{v:"offshore",l:"Offshore",c:T.purple}].map(o=>(
            <label key={o.v} style={{ flex:1,display:"flex",alignItems:"center",gap:7,padding:"9px 10px",borderRadius:7,cursor:"pointer",transition:"all .15s",
              border:`1px solid ${type===o.v?o.c+"60":T.border}`,background:type===o.v?`${o.c}12`:"transparent" }}>
              <input type="radio" name="ptype" value={o.v} checked={type===o.v} onChange={()=>setType(o.v)} style={{ accentColor:o.c }}/>
              <span style={{ fontSize:12,fontWeight:600,color:type===o.v?o.c:T.textSecondary }}>{o.l}</span>
            </label>
          ))}
        </div>
      </div>
      <button disabled={!name.trim()} onClick={()=>name.trim()&&onConfirm({name,type})}
        style={{ padding:"9px 20px",borderRadius:8,border:`1px solid ${name.trim()?T.accent:T.border}`,fontFamily:"'Geist',sans-serif",fontWeight:700,fontSize:13,
          background:name.trim()?T.accent:"transparent",color:name.trim()?"#000":T.textMuted,cursor:name.trim()?"pointer":"not-allowed",opacity:name.trim()?1:.5,transition:"all .15s" }}>
        Create &amp; Upload Files →
      </button>
    </div>
  );
};

// ── File upload ───────────────────────────────────────────────────
const FileUploadWidget = ({ project, onConfirm }) => {
  const [files,setFiles]       = useState([]);
  const [dragging,setDragging] = useState(false);
  const inputRef = useRef();

  const add = (raw) => {
    const entries = Array.from(raw).map(f=>({
      id:uid(),file:f,name:f.name,size:f.size,
      scope: project.type==="onshore"?"onshore":project.type==="offshore"?"offshore":"unassigned",
      orderType:"both",
    }));
    setFiles(p=>[...p,...entries]);
  };

  const untagged   = files.filter(f=>f.scope==="unassigned");
  const canConfirm = files.length>0 && untagged.length===0;

  return (
    <div style={{ background:T.surface,border:`1px solid ${T.border}`,borderRadius:11,padding:16,marginTop:12,maxWidth:560 }}>
      <div style={{ display:"flex",alignItems:"center",gap:8,marginBottom:12 }}>
        <div style={{ width:6,height:6,borderRadius:"50%",background:T.accent }}/>
        <span style={{ fontSize:11,fontWeight:700,color:T.textMuted,textTransform:"uppercase",letterSpacing:"1px" }}>
          Upload Files — <span style={{ color:T.accent }}>{project.name}</span>
        </span>
        <TypeTag type={project.type}/>
      </div>
      <div className={`drop-zone${dragging?" drag":""}`}
        onClick={()=>inputRef.current.click()}
        onDragOver={e=>{e.preventDefault();setDragging(true)}}
        onDragLeave={()=>setDragging(false)}
        onDrop={e=>{e.preventDefault();setDragging(false);add(e.dataTransfer.files)}}>
        <div style={{ fontSize:28,marginBottom:6 }}>📂</div>
        <p style={{ fontSize:13,color:T.textSecondary }}>Drop files or <span style={{ color:T.accent }}>browse</span></p>
        <p style={{ fontSize:11,color:T.textMuted,marginTop:3 }}>PDF, DOCX, XLSX, TXT · 10–20 files</p>
        <input ref={inputRef} type="file" multiple style={{ display:"none" }} onChange={e=>add(e.target.files)} accept=".pdf,.docx,.xlsx,.txt,.csv"/>
      </div>
      {files.length>0 && (
        <div style={{ display:"flex",flexDirection:"column",gap:5,marginBottom:10 }}>
          {project.type==="both" && (
            <div style={{ display:"grid",gridTemplateColumns:"1fr 112px 96px 24px",gap:8,padding:"0 10px 3px",fontSize:10,color:T.textMuted,fontWeight:700,textTransform:"uppercase",letterSpacing:"1px" }}>
              <span>File</span><span>Scope</span><span>Order</span><span/>
            </div>
          )}
          {files.map(f=>(
            <div key={f.id} style={{ display:"grid",gridTemplateColumns:project.type==="both"?"1fr 112px 96px 24px":"1fr 96px 24px",gap:8,padding:"6px 10px",background:T.elevated,borderRadius:6,border:`1px solid ${T.border}`,alignItems:"center" }}>
              <div style={{ display:"flex",alignItems:"center",gap:7,minWidth:0 }}>
                <span style={{ fontSize:12,flexShrink:0 }}>📄</span>
                <span style={{ fontSize:12,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap" }}>{f.name}</span>
                <span style={{ fontSize:10,color:T.textMuted,flexShrink:0 }}>{(f.size/1024).toFixed(0)}kb</span>
              </div>
              {project.type==="both" && (
                <select value={f.scope} onChange={e=>setFiles(p=>p.map(x=>x.id===f.id?{...x,scope:e.target.value}:x))}
                  style={{ borderColor:f.scope==="unassigned"?T.red:T.border,background:f.scope==="unassigned"?"rgba(239,68,68,0.1)":undefined,fontSize:11 }}>
                  <option value="unassigned">— Scope</option>
                  <option value="onshore">⬆ Onshore</option>
                  <option value="offshore">🌊 Offshore</option>
                  <option value="both">Both</option>
                </select>
              )}
              <select value={f.orderType} onChange={e=>setFiles(p=>p.map(x=>x.id===f.id?{...x,orderType:e.target.value}:x))} style={{ fontSize:11 }}>
                <option value="both">A + B</option>
                <option value="a">Order A</option>
                <option value="b">Order B</option>
              </select>
              <button onClick={()=>setFiles(p=>p.filter(x=>x.id!==f.id))}
                style={{ background:"none",border:"none",color:T.textMuted,cursor:"pointer",fontSize:15,padding:0,lineHeight:1 }}>×</button>
            </div>
          ))}
          {project.type==="both" && untagged.length>0 && (
            <div style={{ display:"flex",gap:6,paddingTop:4 }}>
              <button className="chip" style={{ fontSize:11,padding:"4px 12px" }} onClick={()=>setFiles(p=>p.map(f=>f.scope==="unassigned"?{...f,scope:"onshore"}:f))}>⬆ All → Onshore</button>
              <button className="chip" style={{ fontSize:11,padding:"4px 12px" }} onClick={()=>setFiles(p=>p.map(f=>f.scope==="unassigned"?{...f,scope:"offshore"}:f))}>🌊 All → Offshore</button>
            </div>
          )}
        </div>
      )}
      <div style={{ display:"flex",justifyContent:"space-between",alignItems:"center" }}>
        <span style={{ fontSize:12,color:untagged.length>0?T.red:files.length>0?T.green:T.textMuted }}>
          {files.length===0?"No files selected":untagged.length>0?`⚠ ${untagged.length} need scope tagging`:`✓ ${files.length} files ready`}
        </span>
        <button disabled={!canConfirm} onClick={()=>canConfirm&&onConfirm(files)}
          style={{ padding:"8px 18px",borderRadius:8,border:`1px solid ${canConfirm?T.accent:T.border}`,fontFamily:"'Geist',sans-serif",fontWeight:700,fontSize:13,cursor:canConfirm?"pointer":"not-allowed",
            background:canConfirm?T.accent:"transparent",color:canConfirm?"#000":T.textMuted,opacity:canConfirm?1:.5,transition:"all .15s" }}>
          ⚡ Upload &amp; Run Pipeline →
        </button>
      </div>
    </div>
  );
};

// ── Pipeline ──────────────────────────────────────────────────────
const PipelineWidget = ({ stageStates, progress, log, done }) => (
  <div style={{ background:T.surface,border:`1px solid ${done?T.green+"50":T.border}`,borderRadius:10,padding:16,marginTop:10,minWidth:340 }}>
    <div style={{ display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10 }}>
      <span style={{ fontSize:11,fontWeight:700,color:T.textMuted,textTransform:"uppercase",letterSpacing:"1px" }}>
        {done?"✓ Pipeline Complete":"Processing Pipeline…"}
      </span>
      <span style={{ fontSize:13,fontWeight:700,color:done?T.green:T.accent }} className="mono">{progress}%</span>
    </div>
    <div style={{ height:4,background:T.elevated,borderRadius:2,overflow:"hidden",marginBottom:14 }}>
      <div style={{ height:"100%",borderRadius:2,background:done?T.green:T.accent,width:`${progress}%`,transition:"width .5s ease" }}/>
    </div>
    <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:"4px 14px" }}>
      {PIPELINE_STAGES.map(s=>{
        const st=stageStates[s.id]||"idle";
        return (
          <div key={s.id} style={{ display:"flex",alignItems:"center",gap:8,padding:"3px 0" }}>
            <div className={`si si-${st}`}>{st==="active"?<Spin size={11}/>:st==="done"?"✓":s.icon}</div>
            <span style={{ fontSize:12,color:st==="done"?T.green:st==="active"?T.accent:T.textMuted,fontWeight:st==="active"?600:400 }}>{s.label}</span>
          </div>
        );
      })}
    </div>
    {log.length>0 && (
      <div style={{ marginTop:10,padding:"7px 10px",background:T.bg,borderRadius:6,maxHeight:56,overflow:"hidden" }} className="mono">
        {log.slice(-3).map((l,i)=><div key={i} style={{ fontSize:11,color:l.includes("✓")?T.green:T.textMuted,lineHeight:1.7 }}>{l}</div>)}
      </div>
    )}
  </div>
);

// ── Order generation progress ─────────────────────────────────────
const OrderProgress = ({ orderLabel, currentStep, done }) => (
  <div style={{ background:T.surface,border:`1px solid ${done?T.green+"50":T.border}`,borderRadius:10,padding:16,marginTop:10,maxWidth:420 }}>
    <span style={{ fontSize:11,fontWeight:700,color:T.textMuted,textTransform:"uppercase",letterSpacing:"1px",display:"block",marginBottom:10 }}>
      {done?`✓ ${orderLabel} Generated`:`Generating ${orderLabel}…`}
    </span>
    <div style={{ display:"flex",flexDirection:"column",gap:6 }}>
      {ORDER_STEPS.map((s,i)=>{
        const isDone=i<currentStep,isActive=i===currentStep&&!done;
        return (
          <div key={i} style={{ display:"flex",alignItems:"center",gap:10,opacity:i>currentStep?.35:1 }}>
            <div style={{ width:18,height:18,flexShrink:0,display:"flex",alignItems:"center",justifyContent:"center" }}>
              {isDone?<span style={{ color:T.green,fontSize:13 }}>✓</span>:isActive?<Spin/>:<div style={{ width:5,height:5,borderRadius:"50%",background:T.textMuted }}/>}
            </div>
            <span style={{ fontSize:13,color:isDone?T.textPrimary:isActive?T.accent:T.textMuted }}>{s}</span>
          </div>
        );
      })}
    </div>
  </div>
);

// ── Download card ─────────────────────────────────────────────────
const DownloadCard = ({ label, filename, icon, color, onDownload }) => {
  const [isDownloading, setIsDownloading] = useState(false);
  
  const handleDownload = async () => {
    try {
      setIsDownloading(true);      const encodedFilename = encodeURIComponent(filename);
      const response = await fetch(`/api/orders/download?blob=${encodedFilename}`, {
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.split('/').pop() || `${label}.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
      alert(`❌ Download failed: ${error.message}`);
    } finally {
      setIsDownloading(false);
    }
  };
  
  return (
    <div style={{ background:T.surface,border:`1px solid ${color}30`,borderRadius:10,padding:"14px 18px",minWidth:165 }}>
      <div style={{ fontSize:28,marginBottom:8 }}>{icon}</div>
      <div style={{ fontWeight:700,fontSize:14,marginBottom:2 }}>{label}</div>
      <div style={{ fontSize:11,color:T.textMuted,marginBottom:12 }} className="mono">{filename}</div>
      <button onClick={handleDownload} disabled={isDownloading} style={{ display:"flex",alignItems:"center",justifyContent:"center",gap:6,padding:"7px 14px",borderRadius:7,border:"none",cursor:isDownloading?"wait":"pointer",background:color,color:"#fff",fontSize:12,fontWeight:600,fontFamily:"inherit",width:"100%",opacity:isDownloading?0.7:1 }}>
        {isDownloading ? "⏳ Downloading..." : "⬇ Download"}
      </button>
    </div>
  );
};

// ── Scope selector: Onshore / Offshore / Project (both) ──────────
const SCOPE_OPTIONS = [
  {
    key: "onshore",
    icon: "⬆",
    label: "Onshore",
    desc: "Search onshore-tagged chunks only",
    color: T.blue,
    bg: "rgba(59,130,246,0.1)",
    border: "rgba(59,130,246,0.3)",
  },
  {
    key: "offshore",
    icon: "🌊",
    label: "Offshore",
    desc: "Search offshore-tagged chunks only",
    color: T.purple,
    bg: "rgba(139,92,246,0.1)",
    border: "rgba(139,92,246,0.3)",
  },
  {
    key: "project",
    icon: "◎",
    label: "Project",
    desc: "Search entire project — all scopes",
    color: T.green,
    bg: "rgba(16,185,129,0.1)",
    border: "rgba(16,185,129,0.3)",
  },
];

const ScopeSelector = ({ projectName, projectType, onSelect }) => {
  // If project is onshore-only or offshore-only, only show relevant options
  const options = SCOPE_OPTIONS.filter(o => {
    if (projectType === "onshore")  return o.key !== "offshore";
    if (projectType === "offshore") return o.key !== "onshore";
    return true; // "both" → show all three
  });

  return (
    <div style={{ marginTop: 12, maxWidth: 460 }}>
      <div style={{ fontSize: 11, color: T.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 10 }}>
        Scope filter for <span style={{ color: T.textPrimary }} className="mono">{projectName}</span>
      </div>
      <div style={{ display: "flex", gap: 9 }}>
        {options.map(o => (
          <button key={o.key} onClick={() => onSelect(o.key)}
            style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 7, padding: "14px 10px",
              borderRadius: 9, border: `1px solid ${o.border}`, background: o.bg, cursor: "pointer",
              fontFamily: "'Geist',sans-serif", transition: "all .15s" }}
            onMouseEnter={e => e.currentTarget.style.transform = "translateY(-2px)"}
            onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}>
            <span style={{ fontSize: 24 }}>{o.icon}</span>
            <span style={{ fontWeight: 700, fontSize: 14, color: o.color }}>{o.label}</span>
            <span style={{ fontSize: 11, color: T.textSecondary, textAlign: "center", lineHeight: 1.4 }}>{o.desc}</span>
          </button>
        ))}
      </div>
      {projectType === "both" && (
        <div style={{ marginTop: 8, fontSize: 11, color: T.textMuted, textAlign: "center" }}>
          ◎ Project searches all chunks — onshore + offshore combined
        </div>
      )}
    </div>
  );
};

// ── RAG answer card — scoped to project + scope filter ───────────
const SCOPE_COLORS = { onshore:T.blue, offshore:T.purple, project:T.green };
const SCOPE_ICONS  = { onshore:"⬆", offshore:"🌊", project:"◎" };

const RagAnswerCard = ({ project, question, answer, streaming, scope="project" }) => {
  const scopeLabel = scope === "project" ? "Project (all)" : scope.charAt(0).toUpperCase() + scope.slice(1);
  const scopeColor = SCOPE_COLORS[scope] || T.green;
  const scopeIcon  = SCOPE_ICONS[scope]  || "◎";
  return (
    <div className="rag-card">
      {/* Header row: RAG · project · scope */}
      <div style={{ display:"flex",alignItems:"center",gap:8,marginBottom:12,flexWrap:"wrap" }}>
        <span className="scope-badge">💬 RAG</span>
        <span style={{ fontWeight:700,fontSize:12 }} className="mono">{project.name}</span>
        <TypeTag type={project.type}/>
        {/* Scope badge */}
        <span style={{ display:"inline-flex",alignItems:"center",gap:5,padding:"2px 9px",borderRadius:4,
          background:`${scopeColor}15`,border:`1px solid ${scopeColor}35`,color:scopeColor,fontSize:11,fontWeight:700 }}>
          {scopeIcon} {scopeLabel}
        </span>
        <span style={{ fontSize:11,color:T.green }}>{project.files} chunks</span>
      </div>
      {/* Question */}
      <div style={{ fontSize:12,color:T.textMuted,marginBottom:10,fontStyle:"italic",padding:"7px 10px",background:T.elevated,borderRadius:6,borderLeft:`2px solid ${T.cyan}` }}>
        "{question}"
      </div>
      {/* Answer */}
      <div style={{ fontSize:14,color:T.textPrimary,lineHeight:1.8 }}>
        <RichText text={answer}/>
        {streaming&&<span style={{ animation:"blink 1s infinite",color:T.cyan }}>▌</span>}
      </div>
      {!streaming && (
        <div style={{ display:"flex",gap:6,marginTop:12,flexWrap:"wrap",alignItems:"center" }}>
          {["View source chunks","Show DI pages","Ask follow-up"].map(l=>(
            <span key={l} style={{ padding:"3px 10px",borderRadius:4,background:T.elevated,border:`1px solid ${T.border}`,fontSize:11,color:T.textMuted,cursor:"pointer" }}>{l}</span>
          ))}
          <span style={{ marginLeft:"auto",fontSize:10,color:T.textMuted }}>
            {scopeIcon} <strong style={{ color:scopeColor }}>{scopeLabel}</strong> · <strong style={{ color:T.cyan }}>{project.name}</strong>
          </span>
        </div>
      )}
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════
// MAIN APP
// ══════════════════════════════════════════════════════════════════
export default function DocFlowChat() {
  const [messages,setMessages] = useState([]);
  const [input,setInput]       = useState("");
  const [busy,setBusy]         = useState(false);
  const [ctx,setCtx] = useState({ mode:null, project:null, queryProject:null, scope:null });
  const bottomRef = useRef();
  const textRef   = useRef();

  const scrollDown = () => setTimeout(()=>bottomRef.current?.scrollIntoView({behavior:"smooth"}),60);

  useEffect(()=>{
    setMessages([{
      id:uid(), role:"assistant", type:"text",
      text:"Hello! I'm **DocFlow**.\n\nWhat would you like to do?",
      widget:{ type:"home" },
    }]);
  },[]);

  useEffect(()=>{ scrollDown(); },[messages]);

  const push = (msg) => { setMessages(p=>[...p,{id:uid(),...msg}]); scrollDown(); };

  const updateLast = (fn) => setMessages(p=>{
    const copy=[...p];
    const i=copy.map(m=>m.role).lastIndexOf("assistant");
    if(i!==-1) copy[i]={...copy[i],...fn(copy[i])};
    return copy;
  });

  const freezeWidget = (widgetType, newWidget) => setMessages(p=>{
    const copy=[...p];
    const i=copy.map(m=>m.widget?.type).lastIndexOf(widgetType);
    if(i!==-1) copy[i]={...copy[i],widget:newWidget};
    return copy;
  });

  const typeText = async (text) => {
    const words=text.split(" "); let built="";
    for(let i=0;i<words.length;i++){
      built+=(i>0?" ":"")+words[i];
      updateLast(m=>({text:built,streaming:true}));
      await delay(14+Math.random()*16);
    }
    updateLast(m=>({streaming:false}));
  };

  // ── HOME: pick mode ───────────────────────────────────────────
  const handleMainPick = async (key) => {
    freezeWidget("home",{ type:"home-done", picked:key });
    push({ role:"user", type:"text", text:key==="generate"?"Generate Orders":"Query Documents" });
    await delay(300);

    if(key==="generate"){
      setCtx({ mode:"generate", project:null, queryProject:null });
      push({ role:"assistant", type:"text",
        text:"Is this for a **new project** (upload + pipeline) or an **existing indexed project**?",
        widget:{ type:"new-or-old" } });
    } else {
      setCtx({ mode:"query", project:null, queryProject:null });
      push({ role:"assistant", type:"text",
        text:"Type your **project name** to search the index. Your query will be answered **only from that project's vector store** — no cross-project data.",
        widget:{ type:"query-project-search" } });
    }
  };

  // ── GENERATE: new or old ──────────────────────────────────────
  const handleNewOrOld = async (key) => {
    freezeWidget("new-or-old",{ type:"done-badge", label:key==="new"?"New Project":"Existing Project" });
    push({ role:"user", type:"text", text:key==="new"?"New project":"Existing project" });
    await delay(300);

    if(key==="new"){
      push({ role:"assistant", type:"text",
        text:"Set up your new project — name and type. File upload is the next step.",
        widget:{ type:"new-project-form" } });
    } else {
      push({ role:"assistant", type:"text",
        text:"Type your **project name** to search the SQLite registry. I'll look up which orders already exist in the Blob output container.",
        widget:{ type:"old-project-search" } });
    }
  };

  // ── OLD PROJECT: selected → ask scope ────────────────────────
  const handleOldProjectSelected = async (proj) => {
    freezeWidget("old-project-search",{ type:"done-badge", label:`Found: ${proj.name}` });
    setCtx(p=>({...p, project:proj }));
    push({ role:"user", type:"text", text:`Selected: ${proj.name}` });
    await delay(300);
    push({ role:"assistant", type:"text",
      text:`Connected to **${proj.name}** (SQLite ✓ · Blob ✓).\n\nWhich scope should the order cover?`,
      widget:{ type:"scope-selector", project:proj, nextFlow:"old-orders" } });
  };

  // ── SCOPE selected → branch to correct next step ──────────────
  const handleScopeSelected = async (scope, proj, nextFlow) => {
    const scopeLabel = scope === "project" ? "Project (all scopes)" : scope.charAt(0).toUpperCase() + scope.slice(1);
    freezeWidget("scope-selector",{ type:"done-badge", label:`Scope: ${scopeLabel}` });
    setCtx(p=>({...p, scope }));
    push({ role:"user", type:"text", text:`Scope: ${scopeLabel}` });
    await delay(300);

    if(nextFlow === "old-orders"){
      push({ role:"assistant", type:"text",
        text:`Scope set to **${scopeLabel}**. Here are the orders in the output container:`,
        widget:{ type:"old-project-orders", project:proj, scope } });

    } else if(nextFlow === "new-order-choice"){
      push({ role:"assistant", type:"text",
        text:`Scope: **${scopeLabel}**. Which order would you like to generate?`,
        widget:{ type:"order-choice", proj, scope } });

    } else if(nextFlow === "query"){
      push({ role:"assistant", type:"text", text:"", streaming:true });
      await typeText(`Scope locked to **${scopeLabel}** · Project **${proj.name}**.\n\nAsk me anything — I will search only **${proj.name}**'s vector index filtered to ${scopeLabel} chunks.`);
      updateLast(m=>({ streaming:false,
        suggestions:["What is the project scope?","Show cost breakdown","List key deliverables","What are the deadlines?"] }));
      setBusy(false);
    }
  };

  // ── OLD PROJECT: generate a missing order ─────────────────────
  const handleGenerateMissingOrder = async (orderKey, proj) => {
    freezeWidget("old-project-orders",{ type:"done-badge", label:`Generating Order ${orderKey.toUpperCase()}` });
    push({ role:"user", type:"text", text:`Generate Order ${orderKey.toUpperCase()} for ${proj.name}` });
    await delay(300);
    push({ role:"assistant", type:"text",
      text:`Generating **Order ${orderKey.toUpperCase()}** for **${proj.name}** using the existing RAG vector index…`,
      widget:{ type:"order-progress", orderLabel:`Order ${orderKey.toUpperCase()}`, currentStep:0, done:false } });
    await runOrderGeneration();
    await delay(300);
    push({ role:"assistant", type:"text", text:`✅ Done!`,
      widget:{ type:"single-download",
        label:`Order ${orderKey.toUpperCase()}`,
        filename:`${proj.name}_Order_${orderKey.toUpperCase()}.docx`,
        icon:orderKey==="a"?"📄":"📋",
        color:orderKey==="a"?T.blue:T.purple,
        onDownload:()=>alert(`Downloading ${proj.name}_Order_${orderKey.toUpperCase()}.docx`) },
      suggestions:["Generate another order","Query this project","Start over"] });
    setBusy(false);
  };

  // ── NEW PROJECT: form ─────────────────────────────────────────
  const handleNewProjectConfirmed = async ({name,type}) => {
    freezeWidget("new-project-form",{ type:"done-badge", label:`${name} · ${type}` });
    const proj={ id:uid(), name, type, files:0, indexed:false, orders:{ a:null, b:null } };
    setCtx(p=>({...p, project:proj }));
    push({ role:"user", type:"text", text:`Project: ${name} (${type})` });
    await delay(300);
    push({ role:"assistant", type:"text",
      text:`✓ **${name}** created. Upload your source files and tag each with scope + order type.`,
      widget:{ type:"file-upload", project:proj } });
  };

  // ── NEW PROJECT: files → pipeline ────────────────────────────
  const handleFilesConfirmed = async (proj, files) => {
    freezeWidget("file-upload",{ type:"done-badge", label:`${files.length} files uploaded` });
    push({ role:"user", type:"text", text:`${files.length} files uploaded and tagged` });
    await delay(300);
    push({ role:"assistant", type:"text",
      text:`✓ **${files.length} files** received. Starting full pipeline — DI → Chunking → Vector Index → RAG.`,
      widget:{ type:"pipeline", stageStates:{}, progress:0, log:[], done:false } });
    await runPipeline(proj);
  };

  // ── PIPELINE ──────────────────────────────────────────────────
  const runPipeline = async (proj) => {
    const stages=PIPELINE_STAGES.map(s=>s.id);
    for(let i=0;i<stages.length;i++){
      await delay(800+Math.random()*600);
      setMessages(p=>{
        const copy=[...p];
        const idx=copy.map(m=>m.widget?.type).lastIndexOf("pipeline");
        if(idx===-1) return copy;
        const ns={...copy[idx].widget.stageStates};
        if(i>0) ns[stages[i-1]]="done";
        ns[stages[i]]="active";
        const log=[...copy[idx].widget.log,`${new Date().toLocaleTimeString()} ▶ ${PIPELINE_STAGES[i].label}`];
        copy[idx]={...copy[idx],widget:{...copy[idx].widget,stageStates:ns,progress:Math.round(((i+.5)/stages.length)*100),log}};
        return copy;
      });
    }
    await delay(500);
    setMessages(p=>{
      const copy=[...p];
      const idx=copy.map(m=>m.widget?.type).lastIndexOf("pipeline");
      if(idx===-1) return copy;
      const allDone={}; stages.forEach(s=>{allDone[s]="done";});
      const log=[...copy[idx].widget.log,`${new Date().toLocaleTimeString()} ✓ Vector index ready`];
      copy[idx]={...copy[idx],widget:{...copy[idx].widget,stageStates:allDone,progress:100,log,done:true}};
      return copy;
    });
    setCtx(p=>({...p, project:{...p.project,...proj,indexed:true}}));
    await delay(400);
    push({ role:"assistant", type:"text", text:"", streaming:true });
    await typeText(`🎉 **${proj.name}** is fully indexed! Vector index is ready.\n\nWhich scope should the order cover?`);
    updateLast(m=>({ streaming:false,
      widget:{ type:"scope-selector", project:{...proj,indexed:true}, nextFlow:"new-order-choice" },
      suggestions:[] }));
  };

  // ── Order A / B choice (after new project pipeline) ───────────
  const handleOrderChoice = async (orderKey, proj, scope="project") => {
    const scopeLabel = scope === "project" ? "Project" : scope.charAt(0).toUpperCase() + scope.slice(1);
    freezeWidget("order-choice",{ type:"done-badge", label:`Order ${orderKey.toUpperCase()} · ${scopeLabel}` });
    push({ role:"user", type:"text", text:`Generate Order ${orderKey.toUpperCase()} (${scopeLabel})` });
    await delay(300);
    push({ role:"assistant", type:"text",
      text:`Generating **Order ${orderKey.toUpperCase()}** for **${proj.name}** · scope: **${scopeLabel}**…`,
      widget:{ type:"order-progress", orderLabel:`Order ${orderKey.toUpperCase()}`, currentStep:0, done:false } });
    
    // Actually call the backend API
    const generatedFile = await runOrderGeneration(proj.name, orderKey);
    
    await delay(300);
    
    if (generatedFile) {
      push({ role:"assistant", type:"text", text:"✅ Ready to download:",
        widget:{ type:"single-download",
          label:`Order ${orderKey.toUpperCase()}`,
          filename:generatedFile,
          icon:orderKey==="a"?"📄":"📋",
          color:orderKey==="a"?T.blue:T.purple,
          onDownload:()=>alert(`Downloading ${generatedFile}`) },
        suggestions:["Generate the other order","Query this project","Start over"] });
    } else {
      push({ role:"assistant", type:"text", text:"⚠️ Order generation failed. Please try again.",
        suggestions:["Try again","Query this project","Start over"] });
    }
    setBusy(false);
  };

  const runOrderGeneration = async (projectName, orderKey) => {
    try {      
      // Simulate generation progress
      for(let i=0;i<ORDER_STEPS.length;i++){
        await delay(700+Math.random()*450);
        setMessages(p=>{
          const copy=[...p];
          const idx=copy.map(m=>m.widget?.type).lastIndexOf("order-progress");
          if(idx===-1) return copy;
          copy[idx]={...copy[idx],widget:{...copy[idx].widget,currentStep:i+1}};
          return copy;
        });
      }
      
      setMessages(p=>{
        const copy=[...p];
        const idx=copy.map(m=>m.widget?.type).lastIndexOf("order-progress");
        if(idx!==-1) copy[idx]={...copy[idx],widget:{...copy[idx].widget,done:true}};
        return copy;
      });
      
      // Fetch actual generated files from backend
      const response = await fetch(`/api/projects/${projectName}`, {
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        console.error('Failed to fetch project orders');
        return null;
      }
      
      const data = await response.json();
      
      // Return the correct order file
      if (orderKey === "a" && data.orders?.order_a) {
        return data.orders.order_a;
      } else if (orderKey === "b" && data.orders?.order_b) {
        return data.orders.order_b;
      }
      
      return null;
    } catch (error) {
      console.error('Order generation error:', error);
      return null;
    }
  };

  // ── QUERY: project selected → ask scope ──────────────────────
  const handleQueryProjectSelected = async (proj) => {
    freezeWidget("query-project-search",{ type:"done-badge", label:`Scoped to ${proj.name}` });
    setCtx(p=>({...p, queryProject:proj }));
    push({ role:"user", type:"text", text:`Query project: ${proj.name}` });
    await delay(300);
    push({ role:"assistant", type:"text",
      text:`Found **${proj.name}** (${proj.files} indexed chunks · ${proj.type}).\n\nChoose which scope to query:`,
      widget:{ type:"scope-selector", project:proj, nextFlow:"query" } });
  };

  // ── QUERY: answer question (scoped to project + scope) ────────
  const answerQuery = async (question, proj) => {
  push({ role: "user", type: "text", text: question });
  await delay(400);
  
  const scope = ctx.scope || "project";
  
  push({
    role: "assistant",
    type: "text",
    text: "",
    widget: {
      type: "rag-answer",
      project: proj,
      question,
      answer: "Searching project documents...",
      streaming: true,
      scope
    }
  });

  try {
    console.log(`[Chat] Sending to backend: project='${proj.name}', question='${question}'`);
    
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: question,
        project_name: proj.name
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Chat] API error ${response.status}:`, errorText);
      throw new Error(`API returned ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    console.log(`[Chat] Received response:`, data);
    
    const fullAnswer = data.reply || "No response from server";
    
    if (!fullAnswer || fullAnswer.startsWith("Error")) {
      console.error(`[Chat] Received error response:`, fullAnswer);
      throw new Error(fullAnswer);
    }
    
    const words = fullAnswer.split(" ");
    let built = "";
    
    for (let i = 0; i < words.length; i++) {
      built += (i > 0 ? " " : "") + words[i];
      
      setMessages(p => {
        const copy = [...p];
        const idx = copy.map(m => m.widget?.type).lastIndexOf("rag-answer");
        if (idx !== -1) {
          copy[idx] = {
            ...copy[idx],
            widget: {
              ...copy[idx].widget,
              answer: built,
              streaming: true
            }
          };
        }
        return copy;
      });
      
      await delay(20 + Math.random() * 18);
    }
    
    setMessages(p => {
      const copy = [...p];
      const idx = copy.map(m => m.widget?.type).lastIndexOf("rag-answer");
      if (idx !== -1) {
        copy[idx] = {
          ...copy[idx],
          widget: {
            ...copy[idx].widget,
            streaming: false
          }
        };
      }
      return copy;
    });
    
    updateLast(m => ({
      suggestions: [
        "Ask another question",
        "Change scope",
        "Generate Order A",
        "Generate Order B"
      ]
    }));
    
    console.log(`[Chat] ✅ Answer displayed successfully`);
    
  } catch (error) {
    console.error('[Chat] Error fetching answer:', error);
    
    const errorMessage = error.message || 'Unable to get answer. Please try again.';
    
    updateLast(m => ({
      text: `❌ Error: ${errorMessage}

Please check:
• Project name is correct
• Project has been indexed
• Server is running`,
      streaming: false,
      widget: null
    }));
  }
};;

  // ── TEXT INPUT HANDLER ────────────────────────────────────────
  const handleSend = async (text) => {
    const t=(text||input).trim();
    if(!t||busy) return;
    setInput(""); setBusy(true);

    // If in query mode with project locked in, answer the question
    if(ctx.mode==="query" && ctx.queryProject){
      await answerQuery(t, ctx.queryProject);
      setBusy(false);
      return;
    }

    push({ role:"user", type:"text", text:t });
    await delay(350);
    const lo=t.toLowerCase();

    if(lo.includes("start over")||lo.includes("home")){
      setCtx({ mode:null, project:null, queryProject:null, scope:null });
      push({ role:"assistant", type:"text", text:"Back to the start. What would you like to do?", widget:{ type:"home" } });
    } else if(lo.includes("change scope") && ctx.queryProject){
      // Re-ask scope for the same project
      push({ role:"assistant", type:"text",
        text:`Choose a new scope for **${ctx.queryProject.name}**:`,
        widget:{ type:"scope-selector", project:ctx.queryProject, nextFlow:"query" } });
    } else if(lo.includes("query")||lo.includes("ask")){
      setCtx({ mode:"query", project:null, queryProject:null });
      push({ role:"assistant", type:"text",
        text:"Type your project name — your query will be scoped to that project's vector index only.",
        widget:{ type:"query-project-search" } });
    } else if(lo.includes("generate")||lo.includes("order")){
      setCtx({ mode:"generate", project:null, queryProject:null });
      push({ role:"assistant", type:"text",
        text:"Is this a **new project** or an **existing** one?",
        widget:{ type:"new-or-old" } });
    } else if(lo.includes("download")||lo.includes("files")){
      // Show files from blob storage
      const availableFiles = [
        { name: "NORD-STREAM-7_Order_A.docx", project: "NORD-STREAM-7", type: "Order A", icon: "📄" },
        { name: "NORD-STREAM-7_Order_B.docx", project: "NORD-STREAM-7", type: "Order B", icon: "📋" },
        { name: "DELTA-OFFSHORE-3_Order_B.docx", project: "DELTA-OFFSHORE-3", type: "Order B", icon: "📋" },
        { name: "ALPINE-GRID-2024_Order_A.docx", project: "ALPINE-GRID-2024", type: "Order A", icon: "📄" },
      ];
      push({ role:"assistant", type:"text",
        text:"📦 Available files in blob storage:",
        widget:{ type:"blob-download-files", files:availableFiles } });
    } else {
      push({ role:"assistant", type:"text", text:"", streaming:true });
      await typeText("I can **Generate Orders** (Order A / Order B) or **Query Documents** (project-scoped RAG). What would you like?");
      updateLast(m=>({ streaming:false, widget:{ type:"home" } }));
    }
    setBusy(false);
  };

  // ── RENDER ────────────────────────────────────────────────────
  const renderMsg = (msg) => {
    const w = msg.widget;
    return (
      <div key={msg.id}>
        <Bubble role={msg.role} streaming={msg.streaming && !w}>
          {msg.text && <RichText text={msg.text}/>}

          {w?.type==="home"              && <HomeWidget onPick={k=>{setBusy(false);handleMainPick(k);}}/>}
          {w?.type==="home-done"         && <DoneBadge label={w.picked==="generate"?"📋 Generate Orders":"💬 Query Documents"} />}
          {w?.type==="new-or-old"        && <NewOrOldWidget onPick={k=>{setBusy(false);handleNewOrOld(k);}}/>}

          {/* Scope selector */}
          {w?.type==="scope-selector" && (
            <ScopeSelector
              projectName={w.project.name}
              projectType={w.project.type}
              onSelect={scope => { setBusy(false); handleScopeSelected(scope, w.project, w.nextFlow); }}
            />
          )}

          {/* Old project — search by name */}
          {w?.type==="old-project-search" && (
            <ProjectSearch
              label="Enter Project Name"
              hint="— searches SQLite registry"
              accentColor={T.blue}
              onSelect={p=>{setBusy(false);handleOldProjectSelected(p);}}
            />
          )}

          {/* Old project — Order A / B status from blob */}
          {w?.type==="old-project-orders" && (
            <OldProjectOrders
              project={w.project}
              onDownload={filename=>alert(`Downloading ${filename}`)}
              onGenerate={(key,proj)=>{setBusy(true);handleGenerateMissingOrder(key,proj);}}
            />
          )}

          {/* New project form */}
          {w?.type==="new-project-form"  && <NewProjectForm onConfirm={p=>{setBusy(false);handleNewProjectConfirmed(p);}}/>}

          {/* File upload */}
          {w?.type==="file-upload"       && <FileUploadWidget project={w.project} onConfirm={files=>{setBusy(false);handleFilesConfirmed(w.project,files);}}/>}

          {/* Pipeline */}
          {w?.type==="pipeline"          && <PipelineWidget stageStates={w.stageStates} progress={w.progress} log={w.log} done={w.done}/>}

          {/* Order A/B choice after new project indexed */}
          {w?.type==="order-choice"      && (
            <div style={{ display:"flex",gap:10,marginTop:12 }}>
              {["a","b"].map(k=>(
                <button key={k} className="order-btn" onClick={()=>{setBusy(true);handleOrderChoice(k,w.proj,w.scope);}}>
                  <span style={{ fontSize:24 }}>{k==="a"?"📄":"📋"}</span>
                  <span style={{ fontWeight:700,fontSize:14 }}>Order {k.toUpperCase()}</span>
                  <span style={{ fontSize:11,color:T.textMuted }}>{k==="a"?"Primary order":"Service order"}</span>
                </button>
              ))}
            </div>
          )}

          {/* Order generation progress */}
          {w?.type==="order-progress"    && <OrderProgress orderLabel={w.orderLabel} currentStep={w.currentStep} done={w.done}/>}

          {/* Single download */}
          {w?.type==="single-download"   && (
            <div style={{ marginTop:10 }}>
              <DownloadCard label={w.label} filename={w.filename} icon={w.icon} color={w.color} onDownload={w.onDownload}/>
            </div>
          )}
          

          {/* Blob storage files download */}
          {w?.type==="blob-download-files" && (
            <div style={{ marginTop:12, display:"flex", flexDirection:"column", gap:10 }}>
              {w.files.map((file,i)=>(
                <div key={i} style={{ padding:"12px 14px", background:T.surface, borderRadius:8, border:`1px solid ${T.border}`, display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                    <span style={{ fontSize:20 }}>{file.icon}</span>
                    <div>
                      <div style={{ fontSize:13, fontWeight:600, color:T.textPrimary }}>{file.name}</div>
                      <div style={{ fontSize:11, color:T.textMuted }}>{file.project} · {file.type}</div>
                    </div>
                  </div>
                  <button onClick={()=>{ 
                    const a = document.createElement("a");
                    a.href = `/api/download?file=${encodeURIComponent(file.name)}`;
                    a.download = file.name;
                    a.click();
                  }} style={{ padding:"6px 12px", background:T.accent, color:T.bg, border:"none", borderRadius:6, cursor:"pointer", fontSize:12, fontWeight:600 }}>
                    ⬇️ Download
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Query project search */}
          {w?.type==="query-project-search" && (
            <ProjectSearch
              label="Project Name"
              hint="— query is scoped to this project only"
              accentColor={T.cyan}
              onSelect={p=>{setBusy(false);handleQueryProjectSelected(p);}}
            />
          )}

          {/* RAG answer — scoped to project + scope */}
          {w?.type==="rag-answer"        && (
            <RagAnswerCard project={w.project} question={w.question} answer={w.answer} streaming={w.streaming} scope={w.scope}/>
          )}
           
          {w?.type==="order-ready" && (
  <div style={{
    background: T.surface,
    border: `1px solid ${T.green}25`,
    borderRadius: 8,
    padding: "12px 14px",
    marginTop: 10
  }}>
    <button onClick={async () => {
      try {
        const response = await fetch(
          `/api/orders/download?blob=${encodeURIComponent(w.blobName)}`,
          { headers: { 'Content-Type': 'application/json' } }
        );
        if (!response.ok) throw new Error("Download failed");
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = w.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } catch (error) {
        alert(`Download failed: ${error.message}`);
      }
    }} style={{
      width: "100%",
      padding: "10px",
      background: T.green,
      color: "#000",
      border: "none",
      borderRadius: 6,
      fontWeight: 700,
      cursor: "pointer",
      fontFamily: "'Geist', sans-serif"
    }}>
      ⬇️ Download ({w.filename})
    </button>
  </div>
)}
          {/* Generic done badge */}
          {w?.type==="done-badge"        && <DoneBadge label={w.label}/>}

          {msg.suggestions?.length>0 && <Chips items={msg.suggestions} onPick={s=>handleSend(s)}/>}
        </Bubble>
      </div>
    );
  };

  const scopeLabel = ctx.scope === "project" ? "all scopes" : ctx.scope || "";
  const placeholder = ctx.mode==="query" && ctx.queryProject && ctx.scope
    ? `Ask about ${ctx.queryProject.name} · ${scopeLabel}…`
    : ctx.mode==="query" && ctx.queryProject
    ? `Ask about ${ctx.queryProject.name}…`
    : ctx.mode==="query" ? "Type project name to search…"
    : "Type a message or use the options above…";

  return (
    <>
      <style>{css}</style>
      <div style={{ display:"flex",height:"100vh",overflow:"hidden" }}>

        {/* Sidebar */}
        <aside style={{ width:246,background:T.sidebar,borderRight:`1px solid ${T.border}`,display:"flex",flexDirection:"column",flexShrink:0 }}>
          <div style={{ padding:"16px 14px 12px",borderBottom:`1px solid ${T.border}` }}>
            <div style={{ display:"flex",alignItems:"center",gap:10 }}>
              <div style={{ width:30,height:30,background:T.accent,borderRadius:7,display:"flex",alignItems:"center",justifyContent:"center",fontWeight:800,fontSize:15,color:"#000" }}>D</div>
              <div>
                <div style={{ fontWeight:700,fontSize:14 }}>DocFlow</div>
                <div style={{ fontSize:10,color:T.textMuted }} className="mono">Pipeline Assistant</div>
              </div>
            </div>
          </div>
          <div style={{ padding:"10px 10px 4px" }}>
            <button className="chip" style={{ width:"100%",justifyContent:"center",borderRadius:8 }}
              onClick={()=>{ setMessages([{id:uid(),role:"assistant",type:"text",text:"New conversation. What would you like to do?",widget:{type:"home"}}]); setCtx({mode:null,project:null,queryProject:null,scope:null}); }}>
              ✦ New conversation
            </button>
          </div>
          <div style={{ flex:1,overflowY:"auto",padding:"8px 10px" }}>
            <div style={{ fontSize:10,color:T.textMuted,fontWeight:700,textTransform:"uppercase",letterSpacing:"1.5px",padding:"6px 8px" }}>Recent</div>
            {HISTORY.map(h=>(
              <div key={h.id} className="sb-item">
                <span style={{ flexShrink:0,fontSize:14,marginTop:1 }}>{h.icon}</span>
                <div style={{ minWidth:0 }}>
                  <div style={{ overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",fontSize:13 }}>{h.title}</div>
                  <div style={{ fontSize:10,color:T.textMuted }}>{h.date}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Flow reference */}
          <div style={{ margin:"0 10px 10px",padding:"13px 14px",background:T.surface,borderRadius:9,border:`1px solid ${T.border}` }}>
            <div style={{ fontSize:10,color:T.textMuted,fontWeight:700,textTransform:"uppercase",letterSpacing:"1px",marginBottom:10 }}>How It Works</div>
            {[
              [T.accent,  "📋 Generate Orders"],
              [T.textMuted,"  ├ New → Upload → Pipeline → A/B"],
              [T.textMuted,"  └ Old → Name → Blob lookup → A/B"],
              [T.cyan,    "💬 Query Documents"],
              [T.textMuted,"  └ Name → scoped vector search → answer"],
            ].map(([color,label],i)=>(
              <div key={i} style={{ display:"flex",gap:7,alignItems:"flex-start",padding:"2px 0",fontSize:11,color,lineHeight:1.5 }}>
                <span style={{ flexShrink:0,fontFamily:"monospace",minWidth:14 }}></span>{label}
              </div>
            ))}
          </div>

          <div style={{ padding:"10px 12px",borderTop:`1px solid ${T.border}`,display:"flex",alignItems:"center",gap:10 }}>
            <div style={{ width:28,height:28,borderRadius:"50%",background:T.elevated,border:`1px solid ${T.border}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,color:T.textSecondary,fontWeight:600 }}>JB</div>
            <div style={{ flex:1,minWidth:0 }}>
              <div style={{ fontSize:13,fontWeight:500 }}>Jonas Becker</div>
              <div style={{ fontSize:10,color:T.textMuted }}>Project Manager</div>
            </div>
            <div style={{ width:7,height:7,borderRadius:"50%",background:T.green,boxShadow:`0 0 5px ${T.green}` }}/>
          </div>
        </aside>

        {/* Chat pane */}
        <div style={{ flex:1,display:"flex",flexDirection:"column",overflow:"hidden",background:T.bg }}>
          {/* Top bar */}
          <div style={{ height:50,borderBottom:`1px solid ${T.border}`,display:"flex",alignItems:"center",justifyContent:"space-between",padding:"0 24px",flexShrink:0 }}>
            <div style={{ display:"flex",alignItems:"center",gap:10 }}>
              <span style={{ fontSize:14,fontWeight:600 }}>
                {ctx.queryProject?.name || ctx.project?.name || "DocFlow Assistant"}
              </span>
              {(ctx.queryProject||ctx.project) && <TypeTag type={(ctx.queryProject||ctx.project).type}/>}
              {ctx.scope && ctx.scope !== "project" && (
                <span style={{ fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:4,
                  background: ctx.scope==="onshore"?"rgba(59,130,246,0.12)":"rgba(139,92,246,0.12)",
                  color: ctx.scope==="onshore"?T.blue:T.purple,
                  border:`1px solid ${ctx.scope==="onshore"?"rgba(59,130,246,0.3)":"rgba(139,92,246,0.3)"}` }}>
                  {ctx.scope==="onshore"?"⬆ Onshore":"🌊 Offshore"}
                </span>
              )}
              {ctx.scope === "project" && (ctx.queryProject||ctx.project) && (
                <span style={{ fontSize:11,color:T.green }}>◎ Project scope</span>
              )}
              {ctx.mode==="query"&&ctx.queryProject && <span style={{ fontSize:11,color:T.cyan }}>● Query mode</span>}
              {ctx.mode==="generate"&&ctx.project?.indexed && <span style={{ fontSize:11,color:T.green }}>● Indexed</span>}
            </div>
            <div style={{ display:"flex",gap:7 }}>
              <button className="chip" style={{ fontSize:12,padding:"5px 12px" }} onClick={()=>handleSend("Generate orders")}>📋 Generate Orders</button>
              <button className="chip" style={{ fontSize:12,padding:"5px 12px" }} onClick={()=>handleSend("Query documents")}>💬 Query Documents</button>
              <button className="chip" style={{ fontSize:12,padding:"5px 12px" }} onClick={()=>handleSend("Download files")}>💾 Download Files</button>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex:1,overflowY:"auto",padding:"28px 0" }}>
            <div style={{ maxWidth:800,margin:"0 auto",padding:"0 28px",display:"flex",flexDirection:"column",gap:26 }}>
              {messages.map(renderMsg)}
              {busy && messages[messages.length-1]?.role==="user" && (
                <Bubble role="assistant"><TypingDots/></Bubble>
              )}
              <div ref={bottomRef}/>
            </div>
          </div>

          {/* Input */}
          <div style={{ padding:"12px 28px 20px",flexShrink:0 }}>
            <div style={{ maxWidth:800,margin:"0 auto" }}>
              <div className="input-wrap" style={{ padding:"12px 14px 10px" }}>
                <textarea ref={textRef} rows={1} placeholder={placeholder} value={input}
                  onChange={e=>{ setInput(e.target.value); e.target.style.height="auto"; e.target.style.height=Math.min(e.target.scrollHeight,160)+"px"; }}
                  onKeyDown={e=>{ if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); handleSend(); if(textRef.current) textRef.current.style.height="auto"; }}}
                  style={{ maxHeight:160 }}/>
                <div style={{ display:"flex",justifyContent:"space-between",alignItems:"center",marginTop:8 }}>
                  <span style={{ fontSize:11,color:T.textMuted }}>
                    {ctx.mode==="query" && ctx.queryProject
                      ? <><span style={{ color:T.cyan }}>Scoped: {ctx.queryProject.name}</span>
                          {ctx.scope && <span style={{ marginLeft:6, color:ctx.scope==="onshore"?T.blue:ctx.scope==="offshore"?T.purple:T.green }}>{ctx.scope==="onshore"?"⬆ Onshore":ctx.scope==="offshore"?"🌊 Offshore":"◎ Project"}</span>}
                          {" · "}<span style={{ cursor:"pointer",textDecoration:"underline" }} onClick={()=>setCtx(p=>({...p,queryProject:null,scope:null}))}>change project</span>
                          {" · "}<span style={{ cursor:"pointer",textDecoration:"underline" }} onClick={()=>handleSend("Change scope")}>change scope</span>
                        </>
                      : "Enter to send · Shift+Enter for new line"}
                  </span>
                  <button className="send-btn" disabled={!input.trim()||busy}
                    onClick={()=>{ handleSend(); if(textRef.current) textRef.current.style.height="auto"; }}>↑</button>
                </div>
              </div>
              <p style={{ fontSize:11,color:T.textMuted,textAlign:"center",marginTop:8 }}>
                Query answers are scoped to the selected project's vector index only
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}