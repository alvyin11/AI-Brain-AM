# -*- coding: utf-8 -*-
"""Extracts the super prompt from the n8n v2.2 brain into app/prompts/system.txt.
Re-run whenever the v2.2 prompt changes so both brains stay identical.
The n8n live-context expression tail is stripped; graph.py appends the same
context block at runtime from Supabase."""
import json, os

SRC = r"F:\Claude Code\AM Digital KE Free SEO Audit - DataforSEO\workflows\AM Digital KE — AI Brain v2.2.json"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "prompts", "system.txt")

with open(SRC, encoding="utf-8") as f:
    wf = json.load(f)
agent = next(n for n in wf["nodes"] if "AI Brain Agent" in n["name"])
prompt = agent["parameters"]["options"]["systemMessage"].lstrip("=")

marker = "# LIVE CLIENT CONTEXT"
idx = prompt.find(marker)
assert idx > 0, "context marker not found"
head = prompt[:idx].rstrip()

# LangGraph edition notes: tools not present in this build
head += ("\n\n## LANGGRAPH EDITION NOTES\n"
         "- The tools pipeline_audit, monthly_digest, and read_research_file are not available "
         "in this edition yet. If asked for them, say they are handled in the n8n side for now.\n"
         "- The live client context is appended below automatically; it refreshes every 15 minutes.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(head + "\n")
print("WROTE system.txt |", len(head), "chars")
