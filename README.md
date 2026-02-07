# ChatGPT → Claude Migrator

Migrate your ChatGPT conversation history into Claude's memory system. Runs 100% locally on your Mac — no API keys, no cloud uploads, no dependencies beyond Python.

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey)

## What It Does

Rather than replaying conversations (which Claude's API doesn't support), this tool takes a smarter approach: **context distillation**. It analyzes your entire ChatGPT history and extracts the patterns, preferences, projects, and personal context that matter — then formats them as memory edits you can import directly into Claude.

**Input:** Your ChatGPT data export (`conversations.json`)

**Output:** A `claude_migration_output/` folder containing:

| File | Purpose |
|------|---------|
| `memory_edits.txt` | Concise facts (≤200 chars each) ready to paste into Claude's memory system |
| `migration_report.md` | Full analysis — topic distribution, tech stack, monthly activity, per-topic breakdowns |
| `conversations_summary.md` | Every conversation summarized in reverse chronological order |

## Quick Start (macOS)

### 1. Export Your ChatGPT Data

1. Go to [ChatGPT](https://chat.openai.com/) → **Settings** → **Data Controls** → **Export Data**
2. Click **Export** — you'll receive an email within a few minutes
3. Download the `.zip` file from the email link
4. Unzip it — you need the `conversations.json` file inside

> **Tip:** The export can take a few minutes for large accounts. Check your spam folder if you don't see the email.

### 2. Verify Python Is Installed

macOS comes with Python 3 on recent versions. Open **Terminal** and check:

```bash
python3 --version
```

You should see `Python 3.8` or higher. If not, install it:

```bash
# Option A: Install from python.org
# Download from https://www.python.org/downloads/macos/

# Option B: Install via Homebrew
brew install python3
```

### 3. Download & Run the Migrator

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/chatgpt-claude-migrator.git
cd chatgpt-claude-migrator

# Run it (replace the path with your actual file location)
python3 chatgpt_to_claude.py ~/Downloads/conversations.json
```

That's it. No `pip install`, no virtual environments, no API keys.

### 4. Import into Claude

The tool creates a `claude_migration_output/` folder next to your `conversations.json`. Start with `memory_edits.txt`:

**Option A — Bulk import (recommended):**
1. Open `memory_edits.txt` and review for accuracy
2. Delete or edit anything that's wrong
3. Open [Claude](https://claude.ai) and paste:

> Please add these as memory edits:
>
> [paste the numbered lines from memory_edits.txt]

**Option B — Upload the report:**
1. Upload `migration_report.md` to a Claude conversation
2. Ask: *"This is a summary of my ChatGPT history. Please review and add the most important facts to your memory."*

**Option C — One at a time:**
> Please remember that [fact from memory_edits.txt]

## Example Output

Running the tool on a sample export:

```
════════════════════════════════════════════════════════════
  ChatGPT → Claude Context Migration Tool
════════════════════════════════════════════════════════════

Step 1/4: Loading export...
  Loading conversations.json...
  File size: 42.7 MB
  ✓ Found 847 conversations

Step 2/4: Parsing messages...
  ✓ Parsed 823 conversations (24 skipped — empty)

Step 3/4: Analyzing content...
  ✓ 823 conversations, 4,291 user messages
  ✓ 8 topic categories detected
  ✓ 19 tools/technologies identified
  ✓ 12 personal facts extracted

Step 4/4: Generating reports...
  ✓ claude_migration_output/migration_report.md
  ✓ claude_migration_output/memory_edits.txt
  ✓ claude_migration_output/conversations_summary.md

════════════════════════════════════════════════════════════
  ✓ Migration Complete!
════════════════════════════════════════════════════════════
```

## What Gets Extracted

The tool analyzes your conversations across **10 topic categories**:

- Coding & Development
- AI & Machine Learning
- Career & Professional
- Health & Fitness
- Finance & Investing
- Writing & Content
- Productivity & Tools
- Personal & Lifestyle
- Education & Learning
- General

For each conversation, it captures:
- **Topic classification** (up to 3 categories per conversation)
- **Timeline and activity patterns** (monthly breakdown)
- **Tech stack detection** (50+ tools and technologies recognized)
- **Personal fact extraction** (heuristic regex-based extraction of self-referential statements)
- **GPT model usage** (which models you used and how often)

## Privacy & Security

- **100% local** — nothing leaves your machine
- **No network access** — the script makes zero HTTP requests
- **No dependencies** — pure Python standard library, nothing to install
- **No data collection** — your conversations stay on your disk
- **Review before sharing** — all outputs are plaintext files you review before importing into Claude

## Troubleshooting

### "File not found" error
Make sure you're pointing to the actual `conversations.json` file, not the `.zip`:

```bash
# Wrong
python3 chatgpt_to_claude.py ~/Downloads/chatgpt-export.zip

# Right
python3 chatgpt_to_claude.py ~/Downloads/conversations.json
```

### "Unexpected JSON structure" error
The ChatGPT export format has changed over time. If you hit this error, [open an issue](https://github.com/YOUR_USERNAME/chatgpt-claude-migrator/issues) and include the first few lines of your JSON file (redact any personal content).

### Python version too old
```bash
# Check your version
python3 --version

# If below 3.8, update via Homebrew
brew update && brew upgrade python3
```

### Large export takes a long time
Exports with 1,000+ conversations may take 10–30 seconds to process. This is normal — the tool processes everything in a single pass.

## Project Structure

```
chatgpt-claude-migrator/
├── chatgpt_to_claude.py    # The migration tool (single file, zero deps)
├── README.md               # This file
├── LICENSE                  # MIT License
├── .gitignore
└── docs/
    └── how-claude-memory-works.md
```

## How Claude's Memory Works

Claude's memory system stores concise facts (≤200 characters each, max 30 edits) that persist across conversations. These aren't full conversation replays — they're distilled context like:

- "User is a senior engineer at Acme Corp"
- "User's tech stack: Python, React, PostgreSQL, AWS"
- "User prefers concise, direct communication"

This is why the migrator distills rather than replays — it matches how Claude actually uses context. For more details, see [docs/how-claude-memory-works.md](docs/how-claude-memory-works.md).

## Contributing

Contributions welcome! Some ideas:

- Support for additional ChatGPT export format variations
- Improved personal fact extraction (NLP-based vs regex)
- Interactive mode for reviewing/editing memory edits before export
- Support for ChatGPT's shared conversation links

## License

MIT — see [LICENSE](LICENSE) for details.
