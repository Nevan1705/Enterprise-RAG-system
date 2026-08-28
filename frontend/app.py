"""
================================================================================
Project     : Enterprise RAG System v3
Module      : frontend/app.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Streamlit Enterprise Presentation Frontend. Provides interactive
              dashboards, multi-file drag-and-drop ingestion, 1.5s background
              task auto-polling, dynamic QA testcase generation, formatted Excel
              download widgets, session transcript exports, and system health
              diagnostics with dark-mode glassmorphic aesthetics.
================================================================================
"""
import json
import time
import uuid
import requests
import streamlit as st

API = "http://127.0.0.1:8000"
POLL_INTERVAL = 1.5   # seconds between auto-polls

st.set_page_config(
    page_title="RAG Intelligence Platform v3",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --bg0:#07090e;--bg1:#0c1018;--bg2:#111720;--bg3:#18202e;
  --bd:#1c2840;--bd2:#273855;
  --acc:#3b82f6;--acc2:#2563eb;--acg:rgba(59,130,246,.12);
  --ok:#22c55e;--warn:#f59e0b;--err:#ef4444;--purple:#a78bfa;
  --t1:#dde4f0;--t2:#8595ad;--t3:#3d5068;
  --mono:'JetBrains Mono',monospace;
}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:var(--bg0)!important;}
.main .block-container{padding:1.5rem 2rem;max-width:1500px;}
#MainMenu,footer,header{visibility:hidden;}
.stDeployButton{display:none!important;}

/* Sidebar */
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--bd)!important;}

/* Buttons */
.stButton>button{background:var(--acc)!important;color:#fff!important;border:none!important;border-radius:6px!important;font-weight:600!important;font-family:'Inter',sans-serif!important;transition:all .15s!important;}
.stButton>button:hover{background:var(--acc2)!important;transform:translateY(-1px)!important;}

/* Inputs */
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div,.stNumberInput>div>div>input{background:var(--bg2)!important;border:1px solid var(--bd)!important;color:var(--t1)!important;border-radius:6px!important;font-family:'Inter',sans-serif!important;}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{border-color:var(--acc)!important;box-shadow:0 0 0 2px var(--acg)!important;}

/* Cards */
.card{background:var(--bg2);border:1px solid var(--bd);border-radius:10px;padding:1.25rem 1.5rem;margin-bottom:.875rem;}
.card:hover{border-color:var(--bd2);}

/* Metric cards */
.mc{background:var(--bg2);border:1px solid var(--bd);border-radius:10px;padding:1.25rem;position:relative;overflow:hidden;}
.mc::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--acc),transparent);}
.ml{font-size:.65rem;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.4rem;}
.mv{font-size:1.9rem;font-weight:700;color:var(--t1);font-family:var(--mono);line-height:1;}
.ms{font-size:.68rem;color:var(--t2);margin-top:.2rem;}

/* Page title */
.pt{font-size:1.35rem;font-weight:700;color:var(--t1);margin-bottom:.15rem;}
.ps{font-size:.82rem;color:var(--t2);margin-bottom:1.25rem;}

/* Section header */
.sh{font-size:.64rem;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.12em;margin:1.25rem 0 .6rem;padding-bottom:.4rem;border-bottom:1px solid var(--bd);}

/* Badges */
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 9px;border-radius:999px;font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;}
.b-ok  {background:rgba(34,197,94,.1);color:var(--ok);border:1px solid rgba(34,197,94,.25);}
.b-warn{background:rgba(245,158,11,.1);color:var(--warn);border:1px solid rgba(245,158,11,.25);}
.b-info{background:rgba(59,130,246,.1);color:var(--acc);border:1px solid rgba(59,130,246,.25);}
.b-mute{background:rgba(74,85,104,.15);color:var(--t2);border:1px solid var(--bd);}
.b-err {background:rgba(239,68,68,.1);color:var(--err);border:1px solid rgba(239,68,68,.25);}
.b-pur {background:rgba(167,139,250,.1);color:var(--purple);border:1px solid rgba(167,139,250,.25);}

/* Table */
.rt{width:100%;border-collapse:collapse;}
.rt th{text-align:left;font-size:.62rem;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;padding:.55rem 1rem;border-bottom:1px solid var(--bd);}
.rt td{padding:.7rem 1rem;font-size:.78rem;color:var(--t2);border-bottom:1px solid var(--bd);vertical-align:middle;}
.rt tr:hover td{background:var(--bg3);}
.mono{font-family:var(--mono);font-size:.68rem;color:var(--acc);}
.fname{color:var(--t1);font-weight:500;}

/* Progress bar */
.prog-wrap{background:var(--bg3);border-radius:4px;height:6px;overflow:hidden;margin-top:.4rem;}
.prog-bar{height:6px;border-radius:4px;background:linear-gradient(90deg,var(--acc),#60a5fa);transition:width .4s ease;}

/* Chat */
.cm{display:flex;gap:11px;padding:.875rem 1.1rem;border-radius:10px;border:1px solid var(--bd);margin-bottom:.6rem;}
.cm.usr{background:var(--bg3);border-color:var(--bd2);}
.cm.bot{background:var(--bg2);}
.av{width:29px;height:29px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.78rem;font-weight:700;flex-shrink:0;}
.av.u{background:rgba(59,130,246,.15);color:var(--acc);}
.av.a{background:rgba(34,197,94,.12);color:var(--ok);}
.crole{font-size:.62rem;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:.3rem;}
.ctext{font-size:.83rem;color:var(--t1);line-height:1.65;white-space:pre-wrap;}
.cmeta{margin-top:.55rem;display:flex;gap:.4rem;flex-wrap:wrap;}
.sc{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.25);border-radius:5px;font-size:.62rem;color:var(--acc);font-family:var(--mono);}

/* Alerts */
.al{padding:.65rem 1rem;border-radius:7px;font-size:.78rem;margin-bottom:.55rem;display:flex;align-items:flex-start;gap:7px;}
.al-info{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);color:#93c5fd;}
.al-ok  {background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);color:#86efac;}
.al-warn{background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.2);color:#fcd34d;}
.al-err {background:rgba(239,68,68,.07);border:1px solid rgba(239,68,68,.2);color:#fca5a5;}

/* Log */
.logv{background:#040609;border:1px solid var(--bd);border-radius:7px;padding:.875rem 1.1rem;font-family:var(--mono);font-size:.7rem;max-height:260px;overflow-y:auto;color:var(--t2);line-height:1.9;}
.li{color:#4ade80;}.lw{color:#fb923c;}.le{color:#f87171;}

/* Brand */
.brand{display:flex;align-items:center;gap:9px;padding:.875rem 0 1.2rem;border-bottom:1px solid var(--bd);margin-bottom:1.25rem;}
.bhex{font-size:1.35rem;color:var(--acc);}
.bname{font-size:.875rem;font-weight:700;color:var(--t1);line-height:1.1;}
.bver{font-size:.58rem;color:var(--t3);font-family:var(--mono);}

/* Delete btn */
.del-btn>button{background:rgba(239,68,68,.1)!important;color:var(--err)!important;border:1px solid rgba(239,68,68,.25)!important;font-size:.72rem!important;padding:.3rem .75rem!important;}
.del-btn>button:hover{background:rgba(239,68,68,.22)!important;}

/* Download */
.stDownloadButton>button{background:var(--bg3)!important;color:var(--t1)!important;border:1px solid var(--bd2)!important;border-radius:6px!important;font-weight:600!important;}
.stDownloadButton>button:hover{border-color:var(--acc)!important;color:var(--acc)!important;}

/* Progress override */
.stProgress>div>div{background:var(--acc)!important;}
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:var(--bg1);}
::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:3px;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def g(path, timeout=5):
    try:
        r = requests.get(f"{API}{path}", timeout=timeout)
        r.raise_for_status(); return r.json()
    except Exception as e:
        return {"error": str(e)}

def pj(path, data, timeout=120):
    try:
        r = requests.post(f"{API}{path}", json=data, timeout=timeout)
        r.raise_for_status(); return r.json()
    except Exception as e:
        return {"error": str(e)}

def pf(path, files, timeout=120):
    try:
        r = requests.post(f"{API}{path}", files=files, timeout=timeout)
        r.raise_for_status(); return r.json()
    except Exception as e:
        return {"error": str(e)}

def d(path, timeout=10):
    try:
        r = requests.delete(f"{API}{path}", timeout=timeout)
        r.raise_for_status(); return r.json()
    except Exception as e:
        return {"error": str(e)}

def badge(s):
    m={"queued":("b-info","⏳"),"PENDING":("b-mute","⏳"),"STARTED":("b-warn","⚡"),
       "SUCCESS":("b-ok","✓"),"completed":("b-ok","✓"),"FAILURE":("b-err","✗"),
       "duplicate":("b-mute","⊘"),"healthy":("b-ok","●"),"degraded":("b-warn","●"),
       "groq":("b-info","⚡"),"llamaindex":("b-pur","🔄"),"none":("b-mute","—")}
    cls,icon=m.get(s,("b-mute","●"))
    return f'<span class="badge {cls}">{icon} {s}</span>'

def progress_bar(pct):
    return f'<div class="prog-wrap"><div class="prog-bar" style="width:{pct}%"></div></div>'


# ── State ─────────────────────────────────────────────────────────────────────
for k, v in {
    "page": "Dashboard",
    "chat": [],
    "uploads": [],
    "session_id": str(uuid.uuid4()),
    "confirm_delete": None,
    "active_tasks": {},   # task_id → {name, status, progress, step}
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Auto-poll active tasks ────────────────────────────────────────────────────
def poll_active_tasks():
    """Poll all non-terminal tasks. Returns True if any task is still running."""
    still_running = False
    for tid in list(st.session_state.active_tasks.keys()):
        info = st.session_state.active_tasks[tid]
        if info.get("status") in ("SUCCESS", "FAILURE"):
            continue
        resp = g(f"/upload/status/{tid}")
        if "status" in resp:
            st.session_state.active_tasks[tid].update({
                "status":   resp.get("status", "UNKNOWN"),
                "progress": resp.get("progress", 0),
                "step":     resp.get("step", ""),
            })
            if resp.get("status") not in ("SUCCESS", "FAILURE"):
                still_running = True
        else:
            st.error(f"Cannot connect to the backend server. Make sure `uvicorn` is running. Error: {resp.get('error')}")
            still_running = True
    return still_running


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="brand">
      <span class="bhex">⬡</span>
      <div>
        <div class="bname">RAG Intelligence<br>Platform</div>
        <div class="bver">v1.0.0 · RAG Enterprise</div>
      </div>
    </div>""", unsafe_allow_html=True)

    pages = {"Dashboard":"📊","Upload Center":"📤","Document Library":"📚",
             "Query Interface":"💬"}
    st.markdown('<div class="sh">Navigation</div>', unsafe_allow_html=True)
    for name, icon in pages.items():
        if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True):
            st.session_state.page = name
            st.rerun()

    st.markdown('<div class="sh" style="margin-top:1.5rem">System Status</div>', unsafe_allow_html=True)
    h = g("/health")
    if "error" not in h:
        redis_ok = h.get("redis_connected", False)
        faiss_ok = h.get("faiss_index_exists", False)
        llm_prov = h.get("llm_provider", "groq")
        fallback  = h.get("fallback_available", False)
        st.markdown(f"""
        <div style="font-size:.72rem;color:var(--t2);line-height:2.3;">
          <div>Redis&nbsp;&nbsp;&nbsp; {badge('healthy' if redis_ok else 'degraded')}</div>
          <div>FAISS&nbsp;&nbsp;&nbsp; {badge('healthy' if faiss_ok else 'degraded')}</div>
          <div>LLM&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {badge(llm_prov)}</div>
          <div>Fallback&nbsp; {badge('healthy' if fallback else 'degraded')}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:.72rem;color:var(--err);">⚠ Backend offline</div>', unsafe_allow_html=True)

    # Active task count
    running = sum(1 for t in st.session_state.active_tasks.values()
                  if t.get("status") not in ("SUCCESS","FAILURE"))
    if running:
        st.markdown(f'<div style="margin-top:.75rem;">{badge("STARTED")} {running} task(s) running</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-size:.62rem;color:var(--t3);text-align:center;">RAG Enterprise · RAG v1.0.0</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "Dashboard":
    st.markdown('<div class="pt">System Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Live overview of the document intelligence platform</div>', unsafe_allow_html=True)

    health = g("/health")
    docs   = g("/upload/documents")

    total_docs   = len(docs.get("documents", [])) if "error" not in docs else 0
    total_chunks = health.get("total_chunks", 0)
    redis_ok     = health.get("redis_connected", False)
    faiss_ok     = health.get("faiss_index_exists", False)
    fallback     = health.get("fallback_available", False)

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, label, val, sub in [
        (c1,"Documents",       str(total_docs),   "Unique files indexed"),
        (c2,"Chunks",          str(total_chunks), "384-dim vectors"),
        (c3,"Vector Store",
            f'<span style="color:{"var(--ok)" if faiss_ok else "var(--warn)"};font-size:.9rem;">{"● ONLINE" if faiss_ok else "● OFFLINE"}</span>',
            "FAISS IndexFlatIP"),
        (c4,"Broker",
            f'<span style="color:{"var(--ok)" if redis_ok else "var(--warn)"};font-size:.9rem;">{"● ONLINE" if redis_ok else "● OFFLINE"}</span>',
            "Redis / Celery"),
        (c5,"LLM Fallback",
            f'<span style="color:{"var(--ok)" if fallback else "var(--warn)"};font-size:.9rem;">{"● READY" if fallback else "● N/A"}</span>',
            "LlamaIndex"),
    ]:
        with col:
            st.markdown(f'<div class="mc"><div class="ml">{label}</div><div class="mv">{val}</div><div class="ms">{sub}</div></div>', unsafe_allow_html=True)

    ca, cb = st.columns([3, 2])
    with ca:
        st.markdown('<div class="sh">Indexed Documents</div>', unsafe_allow_html=True)
        dl = docs.get("documents", [])[:10] if "error" not in docs else []
        if dl:
            rows = "".join(
                f'<tr><td class="fname">📄 {d["source"]}</td>'
                f'<td class="mono" title="{d["doc_id"]}">{d["doc_id"][:12]}…</td>'
                f'<td>{badge("completed")}</td></tr>'
                for d in dl
            )
            st.markdown(f'<div class="card" style="padding:0; overflow-x:auto;"><table class="rt"><thead><tr><th>Filename</th><th>Doc ID</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="al al-info">ℹ No documents indexed yet.</div>', unsafe_allow_html=True)
    with cb:
        st.markdown('<div class="sh">Platform Config</div>', unsafe_allow_html=True)
        llm_model_name = health.get("llm_model", "openai/gpt-oss-120b")
        st.markdown(f"""
        <div class="card">
          <div style="font-size:.76rem;line-height:2.3;color:var(--t2);">
            <div style="display:flex;justify-content:space-between;"><span>Primary LLM</span><span class="mono">GROQ {llm_model_name}</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Fallback</span><span class="mono">LlamaIndex</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Max Retries</span><span class="mono">2</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Embedding</span><span class="mono">MiniLM-L6-v2</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Dims</span><span class="mono">384</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Chunk / Overlap</span><span class="mono">500 / 100</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Vector Store</span><span class="mono">FAISS IP</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Deletion</span><span class="mono">Full Rebuild</span></div>
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄  Refresh", use_container_width=True):
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD CENTER  (auto-poll every POLL_INTERVAL seconds)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Upload Center":
    st.markdown('<div class="pt">Upload Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Ingest PDF and DOCX documents — real-time task tracking</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop PDF or DOCX files here",
        type=["pdf","docx","doc"],
        accept_multiple_files=True,
    )

    if uploaded:
        st.markdown(f'<div class="al al-info">📎 {len(uploaded)} file(s): {", ".join(f.name for f in uploaded)}</div>', unsafe_allow_html=True)
        if st.button("⬆  Upload & Process"):
            prog = st.progress(0)
            for i, f in enumerate(uploaded):
                prog.progress((i+1)/len(uploaded))
                resp = pf("/upload/", [("files",(f.name,f.getvalue(),f.type or "application/octet-stream"))])
                if "error" not in resp:
                    for u in resp.get("uploads",[]):
                        tid = u.get("task_id")
                        st.session_state.uploads.append({**u, "name": f.name})
                        if tid:
                            st.session_state.active_tasks[tid] = {
                                "name": f.name,
                                "status": "PENDING",
                                "progress": 0,
                                "step": "Queued",
                            }
                else:
                    st.error(f"{f.name}: {resp['error']}")
            prog.empty()
            st.rerun()

    # Auto-polling tracker
    if st.session_state.active_tasks:
        st.markdown('<div class="sh">⚡ Real-Time Task Tracker</div>', unsafe_allow_html=True)

        still_running = poll_active_tasks()

        for tid, info in st.session_state.active_tasks.items():
            status  = info.get("status","?")
            pct     = info.get("progress", 0) or 0
            step    = info.get("step", "")
            name    = info.get("name","")

            col_n, col_s, col_p = st.columns([2.5, 1.2, 3])
            with col_n:
                st.markdown(f'<div style="font-size:.8rem;color:var(--t1);font-weight:500;padding:.4rem 0;">{name}</div>', unsafe_allow_html=True)
            with col_s:
                st.markdown(f'<div style="padding:.4rem 0;">{badge(status)}</div>', unsafe_allow_html=True)
            with col_p:
                st.markdown(
                    f'<div style="padding:.4rem 0;font-size:.72rem;color:var(--t2);">'
                    f'{step} {f"({pct}%)" if pct else ""}'
                    f'{progress_bar(pct)}</div>',
                    unsafe_allow_html=True,
                )
            
            if status == "SUCCESS":
                st.success(f"✅ {name}: Embedding process and chunking is done!")
                if not info.get("success_shown"):
                    st.toast(f"{name} indexed successfully!")
                    info["success_shown"] = True

        if still_running:
            time.sleep(POLL_INTERVAL)
            st.rerun()  # auto-refresh

        if st.button("✕  Clear Completed"):
            st.session_state.active_tasks = {
                k: v for k, v in st.session_state.active_tasks.items()
                if v.get("status") not in ("SUCCESS","FAILURE")
            }
            st.rerun()

    # Upload log
    if st.session_state.uploads:
        st.markdown('<div class="sh">Upload Log</div>', unsafe_allow_html=True)
        for r in st.session_state.uploads[-10:]:
            if r.get("duplicated"):
                st.markdown(f'<div class="al al-warn">⊘ <b>{r["source"]}</b> — Duplicate already indexed</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="al al-ok">✓ <b>{r["source"]}</b> queued · <span class="mono">{r.get("task_id","")[:20]}…</span></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Document Library":
    st.markdown('<div class="pt">Document Library</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Browse, search and manage indexed documents</div>', unsafe_allow_html=True)

    docs = g("/upload/documents")
    if "error" in docs:
        st.markdown(f'<div class="al al-err">⚠ {docs["error"]}</div>', unsafe_allow_html=True)
    else:
        doc_list = docs.get("documents", [])

        c1, c2 = st.columns([3,1])
        with c1:
            srch = st.text_input("🔍  Filter", placeholder="Search filename or doc_id…")
        with c2:
            if st.button("🔄  Refresh", use_container_width=True): st.rerun()

        if srch:
            doc_list = [d for d in doc_list
                        if srch.lower() in d["source"].lower()
                        or srch.lower() in d["doc_id"].lower()]

        st.markdown(f'<div style="font-size:.68rem;color:var(--t3);margin-bottom:.55rem;">{len(doc_list)} document(s)</div>', unsafe_allow_html=True)

        # Confirm delete modal
        if st.session_state.confirm_delete:
            cdoc = st.session_state.confirm_delete
            st.markdown(f"""
            <div class="card" style="border-color:rgba(239,68,68,.35);background:rgba(239,68,68,.04);">
              <div style="font-size:.88rem;font-weight:600;color:var(--err);margin-bottom:.4rem;">⚠ Confirm Deletion</div>
              <div style="font-size:.8rem;color:var(--t2);">
                Delete ALL chunks for:<br>
                <span class="mono">{cdoc}</span><br><br>
                FAISS index will be <strong style="color:var(--err)">rebuilt</strong>. 
                This action <strong style="color:var(--err)">cannot be undone</strong>.
              </div>
            </div>""", unsafe_allow_html=True)
            cy, cn, _ = st.columns([1,1,4])
            with cy:
                if st.button("🗑  Confirm Delete", key="cy"):
                    r = d(f"/upload/document/{cdoc}")
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"Deleted {cdoc[:16]}… and rebuilt FAISS.")
                    st.session_state.confirm_delete = None
                    time.sleep(0.4)
                    st.rerun()
            with cn:
                if st.button("✕  Cancel", key="cn"):
                    st.session_state.confirm_delete = None
                    st.rerun()

        if doc_list:
            hdr = st.columns([0.4,2.5,1,3.5,1])
            for col, h_txt in zip(hdr,["#","Filename","Type","Doc ID","Action"]):
                col.markdown(f'<div style="font-size:.62rem;font-weight:700;color:var(--t3);text-transform:uppercase;padding:.45rem .2rem;">{h_txt}</div>', unsafe_allow_html=True)

            for i, doc in enumerate(doc_list):
                src = doc["source"]; did = doc["doc_id"]
                ext = src.rsplit(".",1)[-1].upper() if "." in src else "?"
                cols = st.columns([0.4,2.5,1,3.5,1])
                cols[0].markdown(f'<div style="font-size:.7rem;color:var(--t3);padding:.5rem .2rem;">{i+1:02d}</div>', unsafe_allow_html=True)
                cols[1].markdown(f'<div style="font-size:.8rem;color:var(--t1);font-weight:500;padding:.5rem .2rem;">📄 {src}</div>', unsafe_allow_html=True)
                cols[2].markdown(f'<div style="padding:.5rem .2rem;"><span class="badge b-mute">{ext}</span></div>', unsafe_allow_html=True)
                cols[3].markdown(f'<div class="mono" style="padding:.5rem .2rem;" title="{did}">{did[:28]}…</div>', unsafe_allow_html=True)
                with cols[4]:
                    st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{did}", help="Delete document"):
                        st.session_state.confirm_delete = did
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="al al-info">ℹ No documents match.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# QUERY INTERFACE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Query Interface":
    st.markdown('<div class="pt">Query Interface</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Ask questions</div>', unsafe_allow_html=True)

    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        docs = g("/upload/documents")
        opts = ["— All Documents —"] + [f'{d["source"]} ({d["doc_id"][:10]}…)' for d in docs.get("documents",[])]
        dmap = {f'{d["source"]} ({d["doc_id"][:10]}…)': d["doc_id"] for d in docs.get("documents",[])}
        sel  = st.selectbox("📂  Filter by Document", opts)
    with c2:
        kv = st.number_input("Top-K", 1, 20, 5)
    with c3:
        st.text_input("Session", value=st.session_state.session_id[:12]+"…", disabled=True)

    doc_filter = dmap.get(sel) if sel != "— All Documents —" else None

    # Export row
    if st.session_state.chat:
        st.markdown('<div class="sh">Chat Export</div>', unsafe_allow_html=True)
        x1,x2,x3 = st.columns([1,1,4])
        with x1:
            export_data = {"session_id": st.session_state.session_id, "messages": st.session_state.chat}
            st.download_button("⬇ JSON", json.dumps(export_data,indent=2),
                f"session_{st.session_state.session_id[:8]}.json","application/json", use_container_width=True)
        with x2:
            lines=["RAG Chat Transcript",f"Session: {st.session_state.session_id}","="*60,""]
            for m in st.session_state.chat:
                lines+=[f"[{m['role'].upper()}]",m['content']]
                if m.get("sources"): lines+=[f"  Sources: {', '.join(m['sources'])}"]
                if m.get("provider"): lines+=[f"  Provider: {m['provider']}"]
                lines+=[""]
            st.download_button("⬇ TXT","\n".join(lines),
                f"session_{st.session_state.session_id[:8]}.txt","text/plain", use_container_width=True)
        with x3:
            if st.button("🗑  Clear Chat"):
                st.session_state.chat=[]; st.session_state.session_id=str(uuid.uuid4()); st.rerun()

    # Render chat
    if st.session_state.chat:
        st.markdown('<div class="sh">Conversation</div>', unsafe_allow_html=True)
        for msg in st.session_state.chat:
            if msg["role"]=="user":
                st.markdown(f'<div class="cm usr"><div class="av u">U</div><div><div class="crole">You</div><div class="ctext">{msg["content"]}</div></div></div>', unsafe_allow_html=True)
            else:
                chips="".join(f'<span class="sc">📄 {s}</span>' for s in msg.get("sources",[]))
                prov=msg.get("provider","groq")
                st.markdown(
                    f'<div class="cm bot"><div class="av a">AI</div><div style="flex:1">'
                    f'<div class="crole">Assistant</div><div class="ctext">{msg["content"]}</div>'
                    f'<div class="cmeta"><span class="badge b-mute">⬡ {msg.get("chunks_used",0)} chunks</span>'
                    f'{badge(prov)}{chips}</div></div></div>',
                    unsafe_allow_html=True,
                )
                if msg.get("download_url"):
                    dl_url = msg["download_url"]
                    try:
                        file_resp = requests.get(f"{API}{dl_url}", timeout=10)
                        if file_resp.status_code == 200:
                            st.download_button(
                                label="⬇ Download Test Cases (.xlsx)",
                                data=file_resp.content,
                                file_name=dl_url.split("/")[-1],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_{dl_url}"
                            )
                    except:
                        pass

    st.markdown('<div class="sh">Ask a Question</div>', unsafe_allow_html=True)
    with st.form("qf", clear_on_submit=True):
        q = st.text_area("Question", placeholder="e.g. What is forward chaining?", height=88, label_visibility="collapsed")
        sub,_ = st.columns([1,5])
        with sub:
            submitted = st.form_submit_button("⬡  Ask", use_container_width=True)

    if submitted and q.strip():
        st.session_state.chat.append({"role":"user","content":q.strip()})
        with st.spinner("Retrieving and generating answer…"):
            payload={"question":q.strip(),"k":int(kv),"session_id":st.session_state.session_id}
            if doc_filter: payload["doc_id"]=doc_filter
            resp=pj("/query/",payload)
        if "error" in resp:
            st.session_state.chat.append({"role":"assistant","content":f"⚠ {resp['error']}","sources":[],"chunks_used":0,"provider":"error"})
        else:
            msg_data = {
                "role":"assistant","content":resp.get("answer",""),
                "sources":resp.get("sources",[]),"doc_ids_used":resp.get("doc_ids_used",[]),
                "chunks_used":resp.get("chunks_used",0),"provider":resp.get("provider","groq"),
                "mode": resp.get("mode", "chat"),
                "download_url": resp.get("download_url")
            }
            st.session_state.chat.append(msg_data)
            
            if resp.get("mode") == "testcases":
                st.toast(f"✅ Generated {resp.get('total_testcases', 0)} testcases successfully!")
                
        st.rerun()



