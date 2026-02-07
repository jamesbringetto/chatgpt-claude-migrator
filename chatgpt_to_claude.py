#!/usr/bin/env python3
"""
ChatGPT → Claude Context Migration Tool
=========================================
Parses a ChatGPT data export (conversations.json) and distills it into
structured context suitable for importing into Claude's memory system.

Zero dependencies — runs on Python 3.8+ standard library only.

Usage:
    python chatgpt_to_claude.py /path/to/conversations.json

Output (written to same directory as input file):
    - memory_edits.txt            — Concise memory entries ready for Claude
    - migration_report.md         — Full detailed analysis
    - conversations_summary.md    — Per-conversation summaries by topic
"""

import json
import sys
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Set, Tuple, Optional, Any

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Max conversations to show per topic section in the report
MAX_PER_TOPIC = 30

# Max chars to include from a message in summaries
MAX_MSG_PREVIEW = 500

# Topic keyword mappings for classification
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "coding_and_development": [
        "code", "python", "javascript", "react", "api", "function", "debug",
        "error", "script", "programming", "github", "git", "deploy",
        "database", "sql", "html", "css", "node", "npm", "typescript",
        "rust", "java", "docker", "kubernetes", "aws", "backend", "frontend",
        "refactor", "test", "ci/cd", "terminal", "cli", "framework", "sdk",
        "webpack", "vite", "nextjs", "django", "flask", "fastapi", "express",
        "postgres", "mongodb", "redis", "graphql", "rest api", "websocket",
    ],
    "ai_and_machine_learning": [
        "ai", "artificial intelligence", "machine learning", "llm",
        "gpt", "claude", "model", "prompt", "chatgpt", "openai",
        "anthropic", "neural", "training", "fine-tune", "embedding",
        "vector", "rag", "agent", "transformer", "token",
        "inference", "diffusion", "stable diffusion", "midjourney",
        "ai agent", "function calling",
    ],
    "career_and_professional": [
        "resume", "interview", "job", "career", "linkedin", "salary",
        "manager", "leadership", "promotion", "hire", "role", "company",
        "startup", "business", "consulting", "freelance", "client",
        "project management", "agile", "scrum", "stakeholder",
        "performance review", "negotiation", "networking",
    ],
    "health_and_fitness": [
        "health", "fitness", "workout", "exercise", "diet", "nutrition",
        "supplement", "protein", "weight", "muscle",
        "running", "marathon", "cycling", "swimming",
        "sleep", "meditation", "fasting", "calories", "macro",
    ],
    "finance_and_investing": [
        "invest", "stock", "trading", "portfolio", "market", "crypto",
        "bitcoin", "ethereum", "finance", "budget", "savings", "retirement",
        "401k", "ira", "dividend", "broker", "forex",
        "revenue", "profit", "roi", "real estate",
    ],
    "writing_and_content": [
        "write", "blog", "article", "essay", "story", "creative writing",
        "content", "copywriting", "edit", "draft", "outline", "publish",
        "newsletter", "book", "chapter", "narrative", "tone", "voice",
    ],
    "productivity_and_tools": [
        "notion", "obsidian", "todoist", "calendar", "workflow",
        "automation", "zapier", "shortcut", "template",
        "spreadsheet", "organize", "system", "process", "efficiency",
        "time management",
    ],
    "personal_and_lifestyle": [
        "travel", "recipe", "hobby", "family", "relationship", "home",
        "moving", "city", "recommendation", "movie", "music", "game",
        "pet", "car", "shopping", "gift", "vacation", "restaurant",
    ],
    "education_and_learning": [
        "learn", "course", "tutorial", "study", "concept", "explain",
        "textbook", "certification", "degree", "university", "research",
        "paper", "mathematics", "physics", "philosophy", "history",
    ],
}

# Tech/tools to detect for the user's toolchain
TECH_PATTERNS = [
    "python", "javascript", "typescript", "react", "vue", "angular", "svelte",
    "node.js", "nodejs", "next.js", "nextjs", "django", "flask", "fastapi",
    "express", "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "github", "gitlab", "notion", "obsidian", "figma", "slack", "linear",
    "vscode", "neovim", "vim", "postgres", "postgresql", "mongodb", "redis",
    "mysql", "grafana", "prometheus", "jenkins", "vercel", "netlify",
    "supabase", "firebase", "stripe", "tailwind", "langchain",
]


# ═══════════════════════════════════════════════════════════════════════════
# PARSING
# ═══════════════════════════════════════════════════════════════════════════

def load_conversations(filepath: str) -> List[Dict]:
    """Load the ChatGPT export file, handling multiple known formats."""
    print(f"  Loading {filepath}...")
    file_size = os.path.getsize(filepath)
    print(f"  File size: {file_size / (1024*1024):.1f} MB")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ["conversations", "data", "items", "chats"]:
            if key in data:
                conversations = data[key]
                break
        else:
            raise ValueError(
                "Unexpected JSON structure. Expected a list or a dict with "
                "a 'conversations' key. Keys found: " + str(list(data.keys()))
            )
    else:
        raise ValueError(f"Unexpected top-level JSON type: {type(data)}")

    print(f"  ✓ Found {len(conversations)} conversations")
    return conversations


def extract_messages(conversation: Dict) -> List[Dict]:
    """
    Extract ordered messages from a conversation.
    Handles the tree/mapping structure used in ChatGPT exports.
    """
    messages = []
    mapping = conversation.get("mapping", {})

    if mapping:
        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue

            content = msg.get("content", {})
            parts = content.get("parts", [])
            if not parts:
                continue

            role = msg.get("author", {}).get("role", "unknown")
            if role not in ("user", "assistant", "system", "tool"):
                continue

            # Extract text parts only (skip image/file references)
            text_parts = []
            for p in parts:
                if isinstance(p, str):
                    text_parts.append(p)
                elif isinstance(p, dict) and "text" in p:
                    text_parts.append(p["text"])

            text = "\n".join(text_parts).strip()
            if not text:
                continue

            messages.append({
                "role": role,
                "text": text,
                "timestamp": msg.get("create_time"),
                "model": msg.get("metadata", {}).get("model_slug", ""),
            })

    # Fallback: some exports use a flat "messages" list
    if not messages:
        flat_msgs = conversation.get("messages", [])
        for msg in flat_msgs:
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("author", {}).get("role", "unknown"))
                text = msg.get("content", msg.get("text", ""))
                if isinstance(text, dict):
                    text = " ".join(text.get("parts", []))
                if isinstance(text, str) and text.strip() and role in ("user", "assistant"):
                    messages.append({
                        "role": role,
                        "text": text.strip(),
                        "timestamp": msg.get("create_time", msg.get("timestamp")),
                        "model": "",
                    })

    # Sort by timestamp
    messages.sort(key=lambda m: m.get("timestamp") or 0)
    return messages


def parse_all_conversations(conversations: List[Dict]) -> List[Dict]:
    """Parse all conversations into a clean, analyzable structure."""
    parsed = []
    skipped = 0

    for conv in conversations:
        title = conv.get("title") or conv.get("name") or "Untitled"
        create_time = conv.get("create_time")
        update_time = conv.get("update_time")
        messages = extract_messages(conv)

        if not messages:
            skipped += 1
            continue

        user_msgs = [m for m in messages if m["role"] == "user"]
        asst_msgs = [m for m in messages if m["role"] == "assistant"]

        # Detect GPT model used
        models_used = set()
        for m in messages:
            if m.get("model"):
                models_used.add(m["model"])

        parsed.append({
            "title": title,
            "create_time": create_time,
            "update_time": update_time,
            "messages": messages,
            "user_message_count": len(user_msgs),
            "assistant_message_count": len(asst_msgs),
            "total_user_chars": sum(len(m["text"]) for m in user_msgs),
            "total_assistant_chars": sum(len(m["text"]) for m in asst_msgs),
            "total_messages": len(messages),
            "models_used": models_used,
        })

    parsed.sort(key=lambda c: c.get("create_time") or 0)

    print(f"  ✓ Parsed {len(parsed)} conversations ({skipped} skipped — empty)")
    return parsed


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def classify_conversation(conv: Dict) -> List[str]:
    """Classify a conversation into topic categories."""
    # Combine title + first ~10 messages for classification
    text = conv["title"].lower() + " "
    for m in conv["messages"][:10]:
        text += m["text"].lower() + " "

    scores = {}
    for category, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score >= 2:
            scores[category] = score

    if not scores:
        return ["general"]

    sorted_cats = sorted(scores.items(), key=lambda x: -x[1])
    return [cat for cat, _ in sorted_cats[:3]]


def fmt_ts(ts: Optional[float]) -> str:
    """Format Unix timestamp → YYYY-MM-DD."""
    if not ts:
        return "Unknown"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return "Unknown"


def fmt_ts_full(ts: Optional[float]) -> str:
    """Format Unix timestamp → YYYY-MM-DD HH:MM UTC."""
    if not ts:
        return "Unknown"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError, OSError):
        return "Unknown"


def detect_tech_stack(parsed: List[Dict]) -> List[str]:
    """Detect tools and technologies mentioned across all conversations."""
    found: Set[str] = set()
    for conv in parsed:
        combined = " ".join(
            m["text"].lower() for m in conv["messages"] if m["role"] == "user"
        )
        for tech in TECH_PATTERNS:
            if tech in combined:
                found.add(tech)
    return sorted(found)


def extract_personal_facts(parsed: List[Dict]) -> List[str]:
    """
    Heuristically extract personal facts from user messages.
    Looks for self-referential statements.
    """
    facts: List[str] = []
    patterns = [
        (r"(?:i am|i'm) a ([^.!?\n]{5,80})", "User is a {}"),
        (r"(?:i work|i'm working) (?:at|for|on) ([^.!?\n]{5,60})", "User works on/at {}"),
        (r"(?:i live|i'm based|i'm located) (?:in|at) ([^.!?\n]{5,40})", "User lives in {}"),
        (r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)", "User's name is {}"),
        (r"(?:i use|i prefer|my favorite|i mainly use) ([^.!?\n]{5,50})", "User prefers {}"),
        (r"(?:i'm learning|i'm studying|i want to learn) ([^.!?\n]{5,50})", "User is learning {}"),
        (r"(?:my (?:goal|plan) is to) ([^.!?\n]{5,80})", "User's goal: {}"),
    ]

    seen = set()
    for conv in parsed:
        for m in conv["messages"]:
            if m["role"] != "user":
                continue
            text = m["text"]
            for pattern, template in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    match = match.strip().rstrip(",;:")
                    if len(match) < 5 or match.lower() in seen:
                        continue
                    seen.add(match.lower())
                    fact = template.format(match)
                    if len(fact) <= 200:
                        facts.append(fact)

    return facts[:50]  # Cap at 50


def analyze_conversations(parsed: List[Dict]) -> Dict:
    """Perform comprehensive analysis."""
    categorized: Dict[str, List[Dict]] = defaultdict(list)
    monthly_activity: Dict[str, int] = defaultdict(int)

    for conv in parsed:
        for cat in classify_conversation(conv):
            categorized[cat].append(conv)
        if conv.get("create_time"):
            month = fmt_ts(conv["create_time"])[:7]  # YYYY-MM
            monthly_activity[month] += 1

    dates = [c["create_time"] for c in parsed if c.get("create_time")]
    total_user = sum(c["user_message_count"] for c in parsed)
    total_asst = sum(c["assistant_message_count"] for c in parsed)

    # Model usage
    model_counts: Dict[str, int] = defaultdict(int)
    for conv in parsed:
        for model in conv.get("models_used", set()):
            if model:
                model_counts[model] += 1

    return {
        "stats": {
            "total_conversations": len(parsed),
            "total_user_messages": total_user,
            "total_assistant_messages": total_asst,
            "total_user_chars": sum(c["total_user_chars"] for c in parsed),
            "earliest": fmt_ts_full(min(dates)) if dates else "Unknown",
            "latest": fmt_ts_full(max(dates)) if dates else "Unknown",
            "avg_msgs": round((total_user + total_asst) / max(len(parsed), 1), 1),
        },
        "categorized": dict(categorized),
        "category_counts": {c: len(v) for c, v in categorized.items()},
        "monthly_activity": dict(sorted(monthly_activity.items())),
        "model_counts": dict(sorted(model_counts.items(), key=lambda x: -x[1])),
        "tech_stack": detect_tech_stack(parsed),
        "personal_facts": extract_personal_facts(parsed),
    }


# ═══════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def generate_migration_report(parsed: List[Dict], analysis: Dict, out: str) -> str:
    """Generate the full migration report."""
    s = analysis["stats"]
    cats = analysis["category_counts"]
    monthly = analysis["monthly_activity"]
    models = analysis["model_counts"]

    lines = [
        "# ChatGPT → Claude Migration Report",
        "",
        "## Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Conversations | {s['total_conversations']} |",
        f"| Your Messages | {s['total_user_messages']:,} |",
        f"| Assistant Responses | {s['total_assistant_messages']:,} |",
        f"| Avg Messages/Conversation | {s['avg_msgs']} |",
        f"| Total Characters (yours) | {s['total_user_chars']:,} |",
        f"| Date Range | {s['earliest']} → {s['latest']} |",
        "",
    ]

    # Model usage
    if models:
        lines += ["## Models Used", ""]
        for model, count in sorted(models.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"- **{model}**: {count} conversations")
        lines.append("")

    # Monthly activity
    if monthly:
        lines += ["## Monthly Activity", ""]
        for month, count in monthly.items():
            bar = "█" * min(count, 60)
            lines.append(f"  {month}  {bar} {count}")
        lines.append("")

    # Topic distribution
    lines += ["## Topic Distribution", ""]
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        label = cat.replace("_", " ").title()
        bar = "█" * min(count, 50)
        lines.append(f"- **{label}**: {count} {bar}")
    lines.append("")

    # Tech stack
    tech = analysis["tech_stack"]
    if tech:
        lines += ["## Detected Tech Stack", "", ", ".join(tech), ""]

    # Personal facts
    facts = analysis["personal_facts"]
    if facts:
        lines += ["## Auto-Detected Personal Context", "",
                   "(Review for accuracy — heuristic extraction)", ""]
        for f in facts:
            lines.append(f"- {f}")
        lines.append("")

    # Per-topic conversation listings
    lines += ["## Conversations by Topic", ""]
    categorized = analysis["categorized"]
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        label = cat.replace("_", " ").title()
        lines.append(f"### {label} ({count} conversations)")
        lines.append("")

        convs = sorted(categorized[cat], key=lambda c: c.get("create_time") or 0, reverse=True)
        for conv in convs[:MAX_PER_TOPIC]:
            date = fmt_ts(conv.get("create_time"))
            msgs = conv["total_messages"]
            first_user = next((m["text"] for m in conv["messages"] if m["role"] == "user"), "")
            preview = first_user[:MAX_MSG_PREVIEW].replace("\n", " ")
            if len(first_user) > MAX_MSG_PREVIEW:
                preview += "..."

            lines.append(f"**{conv['title']}** — {date} ({msgs} msgs)")
            lines.append(f"> {preview}")
            lines.append("")

        if count > MAX_PER_TOPIC:
            lines.append(f"*...and {count - MAX_PER_TOPIC} more*")
            lines.append("")

    report = "\n".join(lines)
    path = os.path.join(out, "migration_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  ✓ {path}")
    return path


def generate_memory_edits(parsed: List[Dict], analysis: Dict, out: str) -> str:
    """
    Generate concise memory edits suitable for Claude's memory system.
    Each edit ≤200 characters. Max 30 edits suggested.
    """
    edits: List[str] = []
    cats = analysis["category_counts"]
    tech = analysis["tech_stack"]
    facts = analysis["personal_facts"]

    # Category-based edits
    top_cats = sorted(cats.items(), key=lambda x: -x[1])[:5]
    interest_labels = [c.replace("_", " ") for c, _ in top_cats if c != "general"]
    if interest_labels:
        edit = f"User's top interests: {', '.join(interest_labels)}"
        if len(edit) <= 200:
            edits.append(edit)

    # Tech stack
    if tech:
        # Split into chunks that fit 200 chars
        chunk: List[str] = []
        for t in tech:
            test = f"User's tech stack: {', '.join(chunk + [t])}"
            if len(test) > 195:
                if chunk:
                    edits.append(f"User's tech stack: {', '.join(chunk)}")
                chunk = [t]
            else:
                chunk.append(t)
        if chunk:
            edits.append(f"User's tech stack: {', '.join(chunk)}")

    # Personal facts (already formatted and ≤200 chars)
    for fact in facts:
        if len(fact) <= 200:
            edits.append(fact)

    # Key projects from substantive conversations
    substantive = [c for c in parsed if c["total_messages"] >= 8 and c["title"] != "Untitled"]
    substantive.sort(key=lambda c: c.get("update_time") or 0, reverse=True)
    project_titles = []
    for conv in substantive[:10]:
        title = conv["title"]
        if len(title) > 5 and title not in project_titles:
            project_titles.append(title)

    if project_titles:
        edit = f"Key ChatGPT projects: {', '.join(project_titles[:5])}"
        if len(edit) > 200:
            edit = edit[:197] + "..."
        edits.append(edit)

    # Deduplicate and cap at 30
    seen = set()
    unique_edits = []
    for e in edits:
        key = e.lower().strip()
        if key not in seen:
            seen.add(key)
            unique_edits.append(e)
    edits = unique_edits[:30]

    # Build output file
    lines = [
        "# Memory Edits for Claude",
        "#",
        "# Instructions:",
        "#   1. Review each line below for accuracy",
        "#   2. Delete or modify anything incorrect",
        "#   3. Copy the remaining lines and paste into Claude with:",
        "#      'Please add these as memory edits:'",
        "#",
        "# Each line is ≤200 characters to fit Claude's memory system.",
        "# You can have up to 30 memory edits total.",
        "",
    ]

    for i, edit in enumerate(edits, 1):
        lines.append(f"{i:2d}. {edit}")

    lines += [
        "",
        f"# Total: {len(edits)} suggested edits",
        "#",
        "# You can also upload migration_report.md to Claude and ask:",
        "#   'Review this and add the most important facts to your memory'",
    ]

    text = "\n".join(lines)
    path = os.path.join(out, "memory_edits.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  ✓ {path}")
    return path


def generate_conversations_summary(parsed: List[Dict], analysis: Dict, out: str) -> str:
    """Generate per-conversation summaries in reverse chronological order."""
    lines = [
        "# Conversation Summaries",
        "",
        f"Total: {len(parsed)} conversations (reverse chronological)",
        "",
    ]

    for conv in reversed(parsed):
        cats = classify_conversation(conv)
        cat_labels = ", ".join(c.replace("_", " ").title() for c in cats)
        date = fmt_ts(conv.get("create_time"))

        lines.append(f"## {conv['title']}")
        lines.append(f"**{date}** | {conv['total_messages']} messages | Topics: {cat_labels}")
        if conv.get("models_used"):
            lines.append(f"Models: {', '.join(conv['models_used'])}")
        lines.append("")

        # First user message
        first = next((m["text"] for m in conv["messages"] if m["role"] == "user"), "")
        if first:
            preview = first[:600].replace("\n", " ")
            if len(first) > 600:
                preview += "..."
            lines.append(f"> {preview}")
            lines.append("")

        # Key follow-ups for long conversations
        user_msgs = [m["text"] for m in conv["messages"] if m["role"] == "user"]
        if len(user_msgs) > 3:
            lines.append(f"*{len(user_msgs)} user messages. Key follow-ups:*")
            # Sample middle and end
            indices = set()
            if len(user_msgs) > 5:
                indices.add(len(user_msgs) // 3)
                indices.add(2 * len(user_msgs) // 3)
            indices.add(len(user_msgs) - 1)
            indices.discard(0)  # Already showed first

            for idx in sorted(indices):
                preview = user_msgs[idx][:250].replace("\n", " ")
                if len(user_msgs[idx]) > 250:
                    preview += "..."
                lines.append(f"- {preview}")
            lines.append("")

        lines.append("---")
        lines.append("")

    text = "\n".join(lines)
    path = os.path.join(out, "conversations_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  ✓ {path}")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print()
    print("═" * 60)
    print("  ChatGPT → Claude Context Migration Tool")
    print("═" * 60)
    print()

    if len(sys.argv) < 2:
        print("Usage: python chatgpt_to_claude.py <conversations.json>")
        print()
        print("To get your ChatGPT export:")
        print("  1. Go to ChatGPT → Settings → Data Controls → Export Data")
        print("  2. Download the .zip from the email link")
        print("  3. Extract and find conversations.json")
        print()
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"  ✗ File not found: {filepath}")
        sys.exit(1)

    output_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), "claude_migration_output")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Load
    print("Step 1/4: Loading export...")
    conversations = load_conversations(filepath)

    # Step 2: Parse
    print("\nStep 2/4: Parsing messages...")
    parsed = parse_all_conversations(conversations)
    if not parsed:
        print("  ✗ No conversations with messages found. Check file format.")
        sys.exit(1)

    # Step 3: Analyze
    print("\nStep 3/4: Analyzing content...")
    analysis = analyze_conversations(parsed)
    s = analysis["stats"]
    print(f"  ✓ {s['total_conversations']} conversations, "
          f"{s['total_user_messages']:,} user messages")
    print(f"  ✓ {len(analysis['category_counts'])} topic categories detected")
    print(f"  ✓ {len(analysis['tech_stack'])} tools/technologies identified")
    print(f"  ✓ {len(analysis['personal_facts'])} personal facts extracted")

    # Step 4: Generate outputs
    print("\nStep 4/4: Generating reports...")
    r1 = generate_migration_report(parsed, analysis, output_dir)
    r2 = generate_memory_edits(parsed, analysis, output_dir)
    r3 = generate_conversations_summary(parsed, analysis, output_dir)

    # Summary
    print()
    print("═" * 60)
    print("  ✓ Migration Complete!")
    print("═" * 60)
    print()
    print("Generated files:")
    print(f"  1. {r2}")
    print(f"     → Ready-to-use memory edits for Claude (start here)")
    print(f"  2. {r1}")
    print(f"     → Full analysis report")
    print(f"  3. {r3}")
    print(f"     → Per-conversation summaries")
    print()
    print("Next steps:")
    print("  1. Open memory_edits.txt and review for accuracy")
    print("  2. Copy the edits into a Claude conversation:")
    print('     "Please add these as memory edits: [paste]"')
    print("  3. For deeper context, upload migration_report.md to Claude")
    print()


if __name__ == "__main__":
    main()
