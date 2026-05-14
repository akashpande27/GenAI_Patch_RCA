from fastapi import FastAPI, UploadFile, File
from app.embeddings import get_embedding
from app.vector_store import (
    add_to_db,
    query_db,
    clear_session_logs,
    get_kb_by_error_code,
    logs_collection
)
from app.llm import ask_llm
from app.rca import build_prompt
from app.utils import chunk_text
import uuid
import re
import time

app = FastAPI()


# ---------------------------
# 📥 Upload Logs
# ---------------------------
@app.post("/upload-log")
async def upload_log(
    file: UploadFile = File(...),
    session_id: str = "default",
    server_id: str = "server1"
):
    content = await file.read()
    text = content.decode("utf-8")

    chunks = chunk_text(text)

    for chunk in chunks:
        embedding = get_embedding(chunk)
        add_to_db(chunk, embedding, str(uuid.uuid4()), session_id, server_id)

    return {
        "message": f"{len(chunks)} chunks stored successfully"
    }


# ---------------------------
# 🔍 Ask RCA
# ---------------------------
@app.post("/ask")
async def ask_question(
    query: str,
    session_id: str = "default",
    server_id: str = None
):
    start_time = time.time()

    # ---------------------------
    # 🧠 Embedding
    # ---------------------------
    t0 = time.time()
    query_embedding = get_embedding(query)
    print(f"[TIME] Embedding: {time.time() - t0:.2f}s")

    # ---------------------------
    # 🔍 Retrieve logs
    # ---------------------------
    t1 = time.time()
    log_results = query_db(query_embedding, session_id, server_id)
    documents = log_results["documents"][0] if log_results["documents"] else []
    log_context = "\n".join([d for d in documents if d.strip()])
    print(f"[TIME] DB Query: {time.time() - t1:.2f}s")

    # 🚨 No logs → STOP
    if not log_context.strip():
        return {
            "answer": "No logs found for the given session. Please upload logs to perform RCA.",
            "context_used": ""
        }

    # ---------------------------
    # 🔥 Ensure failure signals
    # ---------------------------
    t2 = time.time()
    if not any(k in log_context.lower() for k in ["failed", "error", "exit code"]):
        if server_id:
            all_logs = logs_collection.get(
                where={
                    "$and": [
                        {"session_id": session_id},
                        {"server_id": server_id}
                    ]
                },
                limit=20
            )
        else:
            all_logs = logs_collection.get(
                where={"session_id": session_id},
                limit=20
            )

        extra_docs = all_logs.get("documents", [])

        failure_lines = [
            d for d in extra_docs
            if any(k in d.lower() for k in ["failed", "error", "exit code"])
        ][:3]

        if failure_lines:
            log_context += "\n" + "\n".join(failure_lines)

    print(f"[TIME] Failure scan: {time.time() - t2:.2f}s")

    # ---------------------------
    # 🧠 Extract error codes
    # ---------------------------
    t3 = time.time()
    hex_codes = re.findall(r'0x[0-9a-fA-F]+', log_context)
    exit_codes = re.findall(r'Exit Code:?\s*(-?\d+)', log_context)
    all_codes = list(set(hex_codes + exit_codes))
    print(f"[TIME] Code extraction: {time.time() - t3:.2f}s")

    # ---------------------------
    # 🎯 Match KB ONLY if exact match
    # ---------------------------
    t4 = time.time()
    matched_kb = []

    for code in all_codes:
        kb_results = get_kb_by_error_code(code)
        if kb_results and kb_results.get("documents"):
            matched_kb.extend(kb_results["documents"])

    # ---------------------------
    # ✂️ Trim (NO filtering, only size control)
    # ---------------------------
    log_context = log_context[:1500]

    # ---------------------------
    # 🧠 Build context
    # ---------------------------
    if matched_kb:
        kb_context = "\n".join(matched_kb[:2])[:600]
        combined_context = f"Logs:\n{log_context}\n\nKnown Issues:\n{kb_context}"
    else:
        combined_context = f"Logs:\n{log_context}"

    print(f"[TIME] KB Match: {time.time() - t4:.2f}s")

    # ---------------------------
    # 🤖 LLM
    # ---------------------------
    t5 = time.time()
    print("LLM STARTED")

    prompt = build_prompt(combined_context, query)
    answer = ask_llm(prompt)

    print(f"[TIME] LLM: {time.time() - t5:.2f}s")

    # ---------------------------
    # 🧹 Cleanup
    # ---------------------------
    clear_session_logs(session_id)

    print(f"[TIME] TOTAL: {time.time() - start_time:.2f}s\n")

    return {
        "answer": answer,
        "context_used": combined_context
    }
