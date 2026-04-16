"""
Reply Mirror - AI Agent Fraud Detection System
Multi-agent system for detecting evolving financial fraud
"""

import os
import csv
import json
import ulid
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import Langfuse, observe
from langfuse.langchain import CallbackHandler

load_dotenv()

# ── Model setup ──────────────────────────────────────────────────────────────
model = ChatOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model="gpt-4o-mini",
    temperature=0.1,
    max_tokens=1000,
)

langfuse_client = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://challenges.reply.com/langfuse"),
)

def generate_session_id():
    team = os.getenv("TEAM_NAME", "team").replace(" ", "-")
    return f"{team}-{ulid.new().str}"

def safe_float(val):
    try:
        return float(str(val).replace(",", "").strip())
    except:
        return 0.0

# ── AGENT 1: Rule-Based Heuristic Scanner ────────────────────────────────────
def heuristic_agent(transactions: list) -> list:
    suspicious = []
    sender_stats = {}
    for tx in transactions:
        sid = tx.get("Sender ID", "")
        amt = safe_float(tx.get("Amount", 0))
        if sid not in sender_stats:
            sender_stats[sid] = {"amounts": [], "txs": []}
        sender_stats[sid]["amounts"].append(amt)
        sender_stats[sid]["txs"].append(tx)

    for tx in transactions:
        reasons = []
        amt = safe_float(tx.get("Amount", 0))
        balance = safe_float(tx.get("Balance", 0))
        sid = tx.get("Sender ID", "")
        tx_type = tx.get("Transaction Type", "").lower()
        timestamp = tx.get("Timestamp", "")
        stats = sender_stats.get(sid, {})
        amounts = stats.get("amounts", [amt])
        avg_amt = sum(amounts) / len(amounts) if amounts else amt

        if len(amounts) > 2 and amt > avg_amt * 5:
            reasons.append(f"AMOUNT_SPIKE:{amt:.0f}vs{avg_amt:.0f}")
        if balance < 0:
            reasons.append(f"NEGATIVE_BALANCE:{balance:.0f}")
        elif balance < 10 and amt > 100:
            reasons.append(f"NEAR_ZERO_BALANCE:{balance:.2f}")
        if amt >= 1000 and amt % 100 == 0:
            reasons.append(f"LARGE_ROUND:{amt:.0f}")
        if "T" in timestamp:
            try:
                hour = int(timestamp.split("T")[1][:2])
                if hour < 4:
                    reasons.append(f"LATE_NIGHT:h{hour}")
            except:
                pass
        if tx_type == "withdrawal" and not tx.get("Location", "").strip():
            reasons.append("WITHDRAWAL_NO_LOC")
        if tx_type in ["e-commerce", "ecommerce"] and amt > 2000:
            reasons.append(f"HIGH_ECOMMERCE:{amt:.0f}")
        if len(amounts) > 15:
            reasons.append(f"HIGH_VELOCITY:{len(amounts)}")

        if reasons:
            suspicious.append({**tx, "_reasons": reasons, "_risk_score": len(reasons)})

    suspicious.sort(key=lambda x: x["_risk_score"], reverse=True)
    return suspicious

# ── AGENT 2: LLM Reasoning Agent ─────────────────────────────────────────────
FRAUD_SYSTEM_PROMPT = """You are an expert financial fraud detection AI for MirrorPay.
Analyze suspicious transactions and identify which are truly fraudulent.

Consider: unusual amounts, timing, type/method mismatches, balance patterns, velocity.

Respond ONLY with valid JSON (no markdown): {"fraudulent": ["tx_id_1", "tx_id_2"]}
Be precise — false positives harm innocent customers."""

@observe()
def llm_reasoning_agent(session_id: str, suspicious_batch: list) -> list:
    if not suspicious_batch:
        return []

    batch_text = []
    for tx in suspicious_batch[:20]:
        reasons = tx.get("_reasons", [])
        batch_text.append(
            f"ID:{tx.get('Transaction ID','?')} Type:{tx.get('Transaction Type','?')} "
            f"Amt:{tx.get('Amount','?')} Bal:{tx.get('Balance','?')} "
            f"Time:{tx.get('Timestamp','?')} Flags:{','.join(reasons)}"
        )

    prompt = f"Identify fraudulent transactions from these {len(batch_text)} flagged cases:\n\n" + "\n".join(batch_text)

    langfuse_handler = CallbackHandler()
    response = model.invoke(
        [SystemMessage(content=FRAUD_SYSTEM_PROMPT), HumanMessage(content=prompt)],
        config={
            "callbacks": [langfuse_handler],
            "metadata": {"langfuse_session_id": session_id},
        },
    )

    try:
        text = response.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return result.get("fraudulent", [])
    except Exception as e:
        print(f"  WARNING LLM parse error: {e}")
        return []

# ── AGENT 3: Ensemble Decision Agent ─────────────────────────────────────────
def ensemble_agent(suspicious: list, llm_confirmed: list) -> list:
    confirmed_set = set(llm_confirmed)
    for tx in suspicious:
        if tx.get("_risk_score", 0) >= 4:
            confirmed_set.add(tx.get("Transaction ID", ""))
    confirmed_set.discard("")
    return list(confirmed_set)

# ── Data Loader ───────────────────────────────────────────────────────────────
def load_transactions(csv_path: str) -> list:
    transactions = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append(dict(row))
    print(f"  Loaded {len(transactions)} transactions")
    return transactions

# ── Main Pipeline ─────────────────────────────────────────────────────────────
def run_pipeline(csv_path: str, output_path: str):
    session_id = generate_session_id()
    print(f"\n{'='*55}")
    print(f"Reply Mirror Fraud Detection")
    print(f"Dataset: {csv_path}")
    print(f"Session: {session_id}")
    print(f"{'='*55}")

    transactions = load_transactions(csv_path)

    print("\n[Agent 1] Heuristic scanner...")
    suspicious = heuristic_agent(transactions)
    print(f"  {len(suspicious)} suspicious transactions")

    print("\n[Agent 2] LLM reasoning agent...")
    llm_confirmed = []
    batch_size = 20
    top_suspicious = suspicious[:200]
    batches = [top_suspicious[i:i+batch_size] for i in range(0, len(top_suspicious), batch_size)]

    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}/{len(batches)} ({len(batch)} txs)...")
        confirmed = llm_reasoning_agent(session_id, batch)
        llm_confirmed.extend(confirmed)
        print(f"    {len(confirmed)} confirmed")

    print("\n[Agent 3] Ensemble decision...")
    final_fraud = ensemble_agent(suspicious, llm_confirmed)

    total = len(transactions)
    print(f"  Final: {len(final_fraud)} fraud / {total} total ({len(final_fraud)/total*100:.1f}%)")

    if len(final_fraud) == 0:
        print("  !! WARNING: No fraud detected - invalid output !!")
    elif len(final_fraud) == total:
        print("  !! WARNING: All flagged - invalid output !!")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for tx_id in sorted(final_fraud):
            f.write(tx_id + "\n")

    print(f"\n  Output: {output_path}")
    print(f"  Session ID for submission: {session_id}")
    langfuse_client.flush()
    print(f"  Langfuse flushed OK")

    return final_fraud, session_id

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python main.py <transactions.csv> <output.txt>")
        print("Example: python main.py data/Transactions.csv output/result.txt")
        sys.exit(1)
    run_pipeline(sys.argv[1], sys.argv[2])
