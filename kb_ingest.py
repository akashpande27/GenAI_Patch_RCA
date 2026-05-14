import uuid
import re
from app.embeddings import get_embedding
from app.vector_store import add_kb_entry

known_issues = [
    {
        "issue": "Patch failed with exit code 1603",
        "root_cause": "Missing dependency, pending reboot, or application in use",
        "fix": "Reboot system, ensure dependencies are installed, and retry patch"
    },
    {
        "issue": "Patch installation failed with error 0x800f0922",
        "root_cause": "Insufficient system reserved partition space or connectivity issues",
        "fix": "Increase partition size or check connectivity"
    }
]


def ingest():
    for item in known_issues:
        text = f"""
Issue: {item['issue']}
Root Cause: {item['root_cause']}
Fix: {item['fix']}
"""

        emb = get_embedding(text)

        # 🔥 extract error code automatically
        match = re.search(r'(0x[0-9a-fA-F]+|\b\d{3,}\b)', item["issue"])
        error_code = match.group(0) if match else None

        metadata = {}
        if error_code:
            metadata["error_code"] = error_code

        add_kb_entry(text, emb, str(uuid.uuid4()), metadata)


if __name__ == "__main__":
    ingest()