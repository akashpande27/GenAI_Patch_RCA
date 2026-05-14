from chromadb import PersistentClient

client = PersistentClient(path="chroma_db")

logs_collection = client.get_or_create_collection(name="logs")
kb_collection = client.get_or_create_collection(name="rca_kb")


def add_to_db(text, embedding, id, session_id, server_id):
    logs_collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[id],
        metadatas=[{
            "session_id": session_id,
            "server_id": server_id
        }]
    )


def query_db(query_embedding, session_id, server_id=None):
    # ✅ FIX: Proper Chroma filter
    if server_id:
        where_filter = {
            "$and": [
                {"session_id": session_id},
                {"server_id": server_id}
            ]
        }
    else:
        where_filter = {"session_id": session_id}

    return logs_collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where=where_filter
    )


def add_kb_entry(text, embedding, id, metadata):
    kb_collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[id],
        metadatas=[metadata]
    )


def query_kb(query_embedding):
    return kb_collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )


def get_kb_by_error_code(code):
    return kb_collection.get(where={"error_code": code})


def clear_session_logs(session_id):
    logs_collection.delete(where={"session_id": session_id})