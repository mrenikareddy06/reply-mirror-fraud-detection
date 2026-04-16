# Reply Mirror — AI Agent Fraud Detection System - FOLLOW THE PROMPTS I GAVE TO CLAUDE FILE

> **Reply AI Agent Challenge 2026** | 95th place out of 1,971 teams globally | Top 5% worldwide | 196,801 evaluation points

---

## The Problem

In the futuristic city of Reply Mirror (2087), financial institution MirrorPay processes billions of transactions. AI-powered fraudsters called Mirror Hackers constantly evolve their attack patterns — shifting locations, changing timing, varying amounts — to evade detection.

The challenge: build a multi-agent system that detects fraud in real transaction data, adapts to evolving patterns, and minimizes both false positives (blocking innocent customers) and false negatives (missing actual fraud).

---

## Our Approach — 3-Agent Architecture

### Agent 1: Heuristic Scanner
Fast, free, zero LLM calls. Scans every transaction against 7 rules:

- **Geographic impossibility** — withdrawal at ATM in a city/country the user has never been to
- **Amount spike** — transaction is 4x+ above the user's historical average
- **Emergency transfer** — large transfers with "emergency" description to unknown recipients
- **Late-night no-description e-commerce** — purchases at 1-4am with no merchant description
- **Card test pattern** — small test charge followed immediately by large charge at same merchant
- **Wrong-month labels** — rent payments with incorrect month descriptions sent to alternate IBANs
- **Low-salary anomalies** — students/low-income users making transactions far above their means

### Agent 2: LLM Reasoning Agent
Takes the top suspicious transactions from Agent 1 and sends them to GPT-4o-mini with full user context:
- User's job, salary, home city, residence
- Their normal transaction patterns and averages
- Transaction history for behavioral baseline

The LLM reasons about whether each flagged transaction is genuinely fraudulent or just unusual.

### Agent 3: Ensemble Decision Agent
Combines both signals:
- If LLM confirms fraud → included
- If heuristic score is extremely high (4+ flags) → included regardless
- Everything else → excluded

This architecture keeps costs minimal (most work is rule-based) while using LLM reasoning only where it adds value.

---

## Key Insight

**Geographic impossibility was the strongest fraud signal.**

A user living in Piossasco, Italy cannot simultaneously withdraw cash from ATMs in Bremen, Germany at 1am. A user in Fort Collins, Colorado cannot be at an ATM in Cornebarrieu, France. These cases are physically impossible and were detected with near-perfect precision.

Secondary signals that worked well:
- "Emergency fund transfer" descriptions going to unknown IBANs = social engineering fraud
- Card test patterns (€3.19 charge then €3,368 charge at same merchant same day)
- Duplicate rent payments with wrong month labels going to alternate recipient IBANs

---

## Results

| Dataset | Training Score | Evaluation Score | Max Possible |
|---|---|---|---|
| The Truman Show | 16,147 pts | 33,314 pts | 50,000 pts |
| Brave New World | 101,077 pts | 99,690 pts | 200,000 pts |
| Deus Ex | 102,036 pts | 63,796 pts | 400,000 pts |
| **Total** | **219,262 pts** | **196,801 pts** | **650,000 pts** |

**Final leaderboard position: 95th out of 1,971 teams (top 5% globally)**

---

## Tech Stack

- **Python 3.12**
- **LangChain + LangChain-OpenAI** — LLM orchestration
- **Langfuse v3** — observability, token tracking, cost monitoring
- **GPT-4o-mini via OpenRouter** — LLM reasoning agent
- **ULID** — unique session ID generation
- **python-dotenv** — environment management

---

## How to Run

### Setup
```bash
git clone https://github.com/YOUR_USERNAME/reply-mirror-fraud-detection
cd reply-mirror-fraud-detection

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configure environment
Create a `.env` file:
```
OPENROUTER_API_KEY=your-openrouter-key
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_HOST=https://your-langfuse-host
TEAM_NAME=your-team-name
LANGFUSE_MEDIA_UPLOAD_ENABLED=false
```

### Run on a dataset
```bash
# Extract the dataset zip, find transactions.csv, then:
python main.py path/to/transactions.csv output/results.txt
```

The script will print the Langfuse Session ID at the end — use this when submitting to the challenge platform.

---

## Project Structure

```
reply-mirror-fraud-detection/
├── main.py              # Main pipeline — all 3 agents
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
└── README.md
```

---

## What Each Dataset Contained

**The Truman Show** — 80 transactions, 3 users, simple salary/rent pattern. Fraud = any break from the established pattern (unexpected e-commerce, wrong-IBAN rent payments).

**Brave New World** — 522 transactions, 7 users across Europe and US. Fraud = foreign ATM withdrawals, emergency transfers to unknown recipients, late-night no-description e-commerce.

**Deus Ex** — 2,017 transactions, 12 users. Most complex. Fraud = impossible geographic withdrawals (Italy → Indonesia, France → Pakistan), social engineering emergency transfers, card test + large purchase patterns, duplicate payments to alternate IBANs.

---

## Team

Built in one night during the Reply AI Agent Challenge 2026 (April 17, 2026).

- **Biswanath** — strategy, fraud pattern analysis, agent architecture, system design
- **Mrenika Reddy P** — technical implementation, execution

---

## License

MIT
