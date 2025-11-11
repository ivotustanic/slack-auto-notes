# Slack Auto Notes 📝

Transform messy Slack copy-paste into beautifully organized Obsidian notes with AI-powered summaries.

## Features ✨

- **AI-Powered Organization**: Uses OpenAI to extract links, key points, and create structured summaries
- **Smart Link Extraction**: Finds all shared links with full context about who shared them and why
- **Clean Formatting**: Removes emoji codes, metadata, and technical noise from Slack exports
- **Obsidian Integration**: Creates properly formatted markdown notes with collapsible sections
- **Batch Processing**: Archive multiple channels at once
- **Monthly Organization**: Automatically organizes notes by month in your Obsidian vault

## Quick Start 🚀

### 1. Prerequisites

- Python 3.8+
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))
- [Obsidian Notes](https://obsidian.md/)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/slack-auto-notes.git
cd slack-auto-notes

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create your config file from the template:

```bash
# Copy the template
cp config.ini.template config.ini

# Edit with your settings
nano config.ini  # or use your preferred editor
```

Add your OpenAI API key and Obsidian vault path:

```ini
[openai]
api_key = YOUR_OPENAI_API_KEY_HERE

[obsidian]
vault_path = ~/Documents/Obsidian Vault
```

### 4. Usage

#### Copy from Slack
1. Open any Slack channel or DM
2. Scroll bottom to up to load ~30 days of history while selecting (left click)
3. Copy (Cmd+C / Ctrl+C)

#### Run Slack Auto Notes

**Interactive mode**:
```bash
python notesvibe.py
# Choose option 1 or 2 for file/folder processing
```

**File mode** (save Slack text to file first):
```bash
python notesvibe.py -f slack_export.txt -c "Channel Name"
```

**Batch mode** (process multiple channels):
```bash
# Edit channels_example.txt with your channel list
python notesvibe.py -f channels_example.txt
```

## What You Get 📄

Each archived channel creates a beautiful Obsidian note with:

### AI-Generated Summary
- **🔗 Links & Resources**: All shared links with context about who shared them and why
- **📌 Key Points**: Important discussions, decisions, and action items
- **💬 Summary**: High-level overview of the conversation

### Full Message History
- Clean, Slack-like formatting
- 🔗 indicators for messages containing links
- Collapsible section to save space
- Clickable hyperlinks

### Example Output

Your Slack conversations are transformed into beautiful Obsidian notes:

#### 🔗 Links & Resources Section
All shared links are extracted with full context about who shared them and why:

<img width="478" height="68" alt="image" src="https://github.com/user-attachments/assets/e39267c2-d3c1-439c-bc13-2b86b3f94029" />

#### 📌 Key Points Section  
Important discussions and decisions are highlighted:

<img width="497" height="48" alt="image" src="https://github.com/user-attachments/assets/f2a1d333-e7f1-4b01-a9a0-7cfa55b222ad" />

#### 💬 Summary Section
High-level overview of the conversation:

<img width="506" height="56" alt="image" src="https://github.com/user-attachments/assets/53ca0590-3d64-4262-a652-b21626e0eb4b" />

#### Full Conversation & Raw Text
Collapsible sections preserve the complete message history:

<img width="511" height="155" alt="image" src="https://github.com/user-attachments/assets/eab7b706-a5f1-4a9e-b392-b47bea05e78e" />

## Configuration Options ⚙️

Edit `config.ini` to customize:

```ini
[settings]
model = gpt-4o-mini          # OpenAI model (gpt-4o-mini is fast & cheap)
max_tokens = 2000            # Response length (higher = more detail)
temperature = 0.3            # AI creativity (0.0-1.0)
archive_folder = Slack Archives  # Folder name in your vault
```

## Tips 💡

- **Best Results**: Copy entire conversation from Slack (scroll to top first)
- **Monthly Archives**: Notes are automatically organized by month
- **Index File**: An INDEX.md is created listing all archived channels
- **Cost**: Using gpt-4o-mini costs ~$0.01 per channel archive

## Troubleshooting 🔧

**"No OpenAI API key configured"**
- Edit `config.ini` and add your API key
- Or set environment variable: `export OPENAI_API_KEY=your_key`

**"Obsidian vault not found"**
- Check the path in `config.ini`
- Spaces in paths are fine: `~/Documents/Obsidian Vault`

**Poor formatting**
- Make sure to copy from Slack's main message area
- Avoid copying from thread views or search results

## Privacy & Security 🔒

- All processing happens locally on your machine
- Only the text you provide is sent to OpenAI for summarization
- No data is stored outside your Obsidian vault
- API keys are never transmitted except to OpenAI

## Requirements 📦

- `openai>=1.0.0` - For AI summaries
- `python-dotenv` - For environment variables

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Made with ❤️ for the Obsidian community
