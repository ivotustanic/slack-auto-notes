#!/usr/bin/env python3
"""
Slack Auto Notes - Transform raw Slack copies into organized Obsidian notes with AI
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import openai
import configparser

# Load configuration
config = configparser.ConfigParser()
config_file = Path(__file__).parent / "config.ini"

if config_file.exists():
    config.read(config_file)
    OPENAI_API_KEY = config.get('openai', 'api_key', fallback=None)
    # If config has placeholder, check environment
    if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    vault_path = config.get('obsidian', 'vault_path', fallback="~/Documents/Obsidian Vault")
    OBSIDIAN_VAULT = Path(vault_path).expanduser()
    MODEL = config.get('settings', 'model', fallback="gpt-4o-mini")
    MAX_TOKENS = config.getint('settings', 'max_tokens', fallback=2000)
    TEMPERATURE = config.getfloat('settings', 'temperature', fallback=0.3)
    ARCHIVE_FOLDER = config.get('settings', 'archive_folder', fallback="Slack Archives")
else:
    # Default configuration
    OBSIDIAN_VAULT = Path("~/Documents/Obsidian Vault").expanduser()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = "gpt-4o-mini"
    MAX_TOKENS = 2000
    TEMPERATURE = 0.3
    ARCHIVE_FOLDER = "Slack Archives"
    print("⚠️ Warning: config.ini not found. Please create it from the template.")

if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
    openai.api_key = OPENAI_API_KEY


class NotesVibe:
    def __init__(self):
        self.vault_path = OBSIDIAN_VAULT / ARCHIVE_FOLDER
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
    def parse_slack_text(self, raw_text, channel_name):
        """Parse the raw Slack text into structured messages."""
        lines = raw_text.strip().split('\n')
        messages = []
        current_msg = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Pattern for detecting a new message (author + timestamp)
            # Looking for patterns like "Jo Hoenzsch" followed by timestamp on next line
            # or "Name  11:54 AM" on same line
            time_pattern = r'\d{1,2}:\d{2}\s*[AP]M'
            
            # Check if this is a potential author line (not too long, not a reaction)
            is_potential_author = (
                len(line) < 50 and 
                not line.startswith(':') and 
                not line.startswith('header:') and
                not line.startswith('send:') and
                not line.startswith('reply:') and
                not re.match(r'^\d+$', line)
            )
            
            # Look ahead for timestamp on next line
            if is_potential_author and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Check if next line has emoji prefix and time (like ":no_entry:  9:16 AM")
                if re.search(r':[^:\s]+:\s*\d{1,2}:\d{2}\s*[AP]M', next_line):
                    # Save previous message
                    if current_msg and current_msg['content']:
                        current_msg['content'] = self._clean_message_content(current_msg['content'])
                        if current_msg['content']:
                            messages.append(current_msg)
                    
                    # Author is on current line, time with emoji on next
                    author = line.strip()
                    # Remove emoji from time line
                    time_str = re.sub(r':[^:\s]+:\s*', '', next_line).strip()
                    current_msg = {
                        'author': author,
                        'time': time_str,
                        'content': []
                    }
                    i += 2
                    continue
                elif re.search(time_pattern, next_line):
                    # Save previous message
                    if current_msg and current_msg['content']:
                        current_msg['content'] = self._clean_message_content(current_msg['content'])
                        if current_msg['content']:  # Only add if content remains after cleaning
                            messages.append(current_msg)
                    
                    # Start new message
                    # Clean emoji representations from author
                    author = re.sub(r':[^:\s]+:', '', line.strip()).strip()
                    # Clean emoji from time line too  
                    time_str = re.sub(r':[^:\s]+:\s*', '', next_line.strip()).strip()
                    current_msg = {
                        'author': author if author else line.strip(),  # Fallback to original if empty
                        'time': time_str,
                        'content': []
                    }
                    i += 2
                    continue
            
            # Check if timestamp is in the current line
            if re.search(time_pattern, line):
                # Save previous message
                if current_msg and current_msg['content']:
                    current_msg['content'] = self._clean_message_content(current_msg['content'])
                    if current_msg['content']:
                        messages.append(current_msg)
                
                # Extract author if on same line
                match = re.match(r'(.+?)\s*[-–]\s*(\d{1,2}:\d{2}\s*[AP]M)', line)
                if match:
                    author = match.group(1).strip()
                    time = match.group(2).strip()
                else:
                    author = "Unknown"
                    time = line.strip()
                
                # Clean emoji representations from author
                author = re.sub(r':[^:\s]+:', '', author).strip()
                if not author:
                    author = "Unknown"
                
                current_msg = {
                    'author': author,
                    'time': time,
                    'content': []
                }
                i += 1
                continue
            
            # It's content for the current message
            if current_msg:
                # Skip pure metadata lines
                skip_patterns = [
                    r'^\d+\s+repl(y|ies)',
                    r'^Last reply',
                    r'^View thread',
                    r'^:\w+:\s*\d*$',  # Reactions like ":+1: 2"
                    r'^edited$'
                ]
                
                if not any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                    current_msg['content'].append(line)
            
            i += 1
        
        # Don't forget the last message
        if current_msg and current_msg['content']:
            current_msg['content'] = self._clean_message_content(current_msg['content'])
            if current_msg['content']:
                messages.append(current_msg)
        
        return messages
    
    def _clean_message_content(self, content_lines):
        """Clean and format message content."""
        # Join lines
        content = '\n'.join(content_lines)
        
        # Remove HTTP debug output - it's just noise
        if 'header:' in content or 'send:' in content or 'reply:' in content:
            lines = content.split('\n')
            cleaned = []
            skip_technical = False
            
            for line in lines:
                # Skip all the HTTP debug garbage
                if line.startswith(('header:', 'send:', 'reply:')):
                    skip_technical = True
                    continue
                elif skip_technical and line.strip() and not line.startswith(('header:', 'send:', 'reply:')):
                    # We're past the technical stuff
                    skip_technical = False
                
                if not skip_technical:
                    # Keep actual message content
                    cleaned.append(line)
            
            content = '\n'.join(cleaned)
        
        # Remove emoji text representations like :no_entry:, :thumbs-up:, etc.
        content = re.sub(r':[a-zA-Z0-9_\-]+:', '', content)
        
        # Remove standalone emoji reactions at the end
        content = re.sub(r'\n:[a-z_]+:\s*$', '', content)
        
        # Clean up excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single space
        
        return content.strip()
    
    def create_ai_summary(self, messages, channel_name):
        """Use AI to create organized notes, not just a summary."""
        if not OPENAI_API_KEY:
            return None
            
        print(f"   🤖 Creating organized notes for {channel_name}...")
        
        # Prepare context for AI - give it ALL messages with clear author attribution
        conversation = "\n\n".join([
            f"MESSAGE FROM: {msg.get('author', 'Unknown')}\nTIME: {msg.get('time', 'no time')}\nCONTENT: {msg['content']}\n---"
            for msg in messages  # ALL messages for complete and accurate link extraction
        ])
        
        prompt = f"""You're an expert at parsing messy Slack copy-paste text. Clean it up and organize it.

Channel/DM: {channel_name}

IMPORTANT CLEANING RULES:
- Remove ALL emoji text like :no_entry:, :thumbs-up:, :+1:, :eyes:, etc
- Remove "X replies", "Last reply", "View thread", "edited" metadata  
- Remove reaction counts
- Remove "Owned by", "people viewed", "More actions", "Added by" noise
- Fix spacing issues and garbled text
- Format timestamps consistently
- When a message contains a URL, add 🔗 before the author name to mark it

Create ONLY these 3 sections:

## 🔗 Links & Resources
CRITICAL: The conversation may contain:
1. Full URLs (http:// or https://) - Extract these exactly
2. Link titles without URLs (e.g., "Appendix of Bazel Rules") - Mark these as [Title] (no URL available)
3. References to documents/sites without links - Include these too

RULES:
- Find the EXACT person who shared each link/document by checking MESSAGE FROM
- Use ONLY context from their actual message
- If no URL is provided, write "[Document Name] (link not captured)"
- DO NOT make up URLs or context

FORMAT:
- [Descriptive title for the link](actual_url_here) - **Person Name** - Context from their message
OR if no URL available:
- [Document Title] (link not captured) - **Person Name** - Context from their message

EXAMPLE with URL:
- [Terraform PR](https://github.com/DataDog/terraform-config/pull/40928/files) - **Jo Hoenzsch** - Mentioned issues with CI checks failing

EXAMPLE without URL:
- [Appendix of Bazel Rules] (link not captured) - **Champak Das** - Shared as documentation on common bzl rules

Be ACCURATE - only attribute to the person who actually shared it!

## 📌 Key Points
Create DETAILED bullet points with full context:
- **Topic name** - Complete explanation including WHO said it, WHAT was decided/discussed, WHY it matters, WHEN it happened/deadline
- Include specific names, tools, error messages, decisions
- Each bullet should stand alone - someone should understand it without reading the chat

Example format:
- **Terraform CI issue** - Jo discovered that terraform-config CI checks can be overridden even when failing, causing cascading errors for other PRs. Needs team discussion on enforcement.

## 💬 Summary  
Create organized bullet points (not paragraph) covering:
- **Main discussion themes** - What the conversation focused on
- **Key decisions/outcomes** - What was decided or accomplished  
- **Action items** - What needs to happen next and who's responsible
- **Important context** - Background info for future reference

Conversation (CLEAN THIS UP - remove header:, send:, reply: lines):
{conversation}

CRITICAL: 
- REMOVE all the HTTP debug garbage (header:, send:, reply:)
- Links are the MOST valuable - extract every single one with context
- Keep it simple and CLEAN"""

        try:
            # Use the new OpenAI API format (v2.x)
            import openai
            
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts and organizes information from Slack conversations. CRITICAL RULES: 1) Extract ALL URLs exactly as they appear. 2) ONLY attribute links to the person who actually shared them - check MESSAGE FROM field. 3) Use ONLY the context that actually appears in the messages - DO NOT make up or infer context. 4) If context is unclear, say 'Shared without additional context' rather than guessing."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            summary = response.choices[0].message.content
            print(f"   ✅ AI organized notes created")
            return summary
            
        except Exception as e:
            print(f"   ⚠️ AI error: {e}")
            return None
    
    def format_messages_markdown(self, messages):
        """Format messages to look clean like Slack."""
        formatted = []
        current_date = None
        
        for msg in messages:
            # Get message parts
            author = msg.get('author', 'Unknown')
            time = msg.get('time', '')
            content = msg.get('content', '')
            
            # Skip date separators for now - they're not reliable with copy-paste
            # and make the output messier when they don't work right
            
            # Clean up author name (remove ALL emoji representations like :no_entry:)
            author = re.sub(r':[^:\s]+:', '', author).strip()
            
            # Also clean emoji representations from content
            content = re.sub(r':[^:\s]+:', '', content)
            
            # Add spacing between messages
            if formatted:  # If not the first message
                formatted.append("")  # Add blank line before new message
            
            # Check if content has links
            has_link = 'http://' in content or 'https://' in content
            
            # Format header like Slack: bold author and time (with link indicator if needed)
            if has_link:
                formatted.append(f"### 🔗 {author} • {time}\n")
            else:
                formatted.append(f"### {author} • {time}\n")
            
            # Format content - SIMPLE AND CLEAN
            if content:
                # Clean up the content
                clean_lines = []
                for line in content.split('\n'):
                    line = line.strip()
                    
                    # Skip metadata and reactions
                    if not line:
                        continue
                    if re.match(r'^\d+$', line):  # Just numbers
                        continue
                    if any(skip in line.lower() for skip in ['replies', 'last reply', 'view thread', 'edited', 'added by']):
                        continue
                    if re.match(r'^:\w+:\s*\d*$', line):  # Reactions
                        continue
                    
                    # Remove ALL emoji representations including ones with special chars
                    line = re.sub(r':[^:\s]+:', '', line).strip()
                    if not line:
                        continue
                    
                    # Convert URLs to clickable links (handle URLs in parentheses too)
                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\)]+'
                    urls = re.findall(url_pattern, line)
                    for url in urls:
                        # Clean URL
                        clean_url = url.rstrip('.,;:)')
                        # Create markdown link
                        if 'github.com' in url:
                            line = line.replace(url, f"[GitHub]({clean_url})")
                        elif 'atlassian.net' in url or 'jira' in url.lower():
                            line = line.replace(url, f"[JIRA]({clean_url})")
                        elif 'docs.google.com' in url:
                            line = line.replace(url, f"[Google Doc]({clean_url})")
                        elif 'slack.com' in url:
                            line = line.replace(url, f"[Slack]({clean_url})")
                        else:
                            # Extract domain for label
                            try:
                                domain = clean_url.split('/')[2].replace('www.', '')
                                line = line.replace(url, f"[{domain}]({clean_url})")
                            except:
                                line = line.replace(url, f"[Link]({clean_url})")
                    
                    # Skip image mentions entirely - we don't need them
                    if 'image.png' in line.lower() or '[image attached]' in line.lower():
                        continue
                    else:
                        clean_lines.append(line)
                
                # Add the cleaned content
                if clean_lines:
                    formatted.extend(clean_lines)
            
        return '\n'.join(formatted)
    
    def _format_links(self, text):
        """Format URLs in text as proper markdown links."""
        # Find URLs
        url_pattern = r'(https?://[^\s]+)'
        
        def replace_url(match):
            url = match.group(1)
            # Clean up URL (remove trailing punctuation)
            url = url.rstrip('.,;:)')
            
            # Try to extract a title from the URL
            if 'docs.google.com' in url:
                return f"[📄 Google Doc]({url})"
            elif 'slides.google.com' in url or 'Google Slides' in text:
                return f"[📊 Google Slides]({url})"
            elif 'github.com' in url:
                return f"[🐙 GitHub]({url})"
            elif 'jira' in url.lower():
                return f"[🎫 Jira]({url})"
            else:
                # Generic link
                domain = url.split('/')[2] if '/' in url else url
                return f"[🔗 {domain}]({url})"
        
        return re.sub(url_pattern, replace_url, text)
    
    def save_to_obsidian(self, channel_name, messages, ai_summary=None, raw_text=None):
        """Save everything to Obsidian."""
        print(f"\n💾 Saving {channel_name} to Obsidian...")
        
        # Slack shows up to 30 days of history when copying
        # Calculate date range (last 30 days from today)
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        date_range = f"{thirty_days_ago.strftime('%b %d')} to {today.strftime('%b %d')}"
        
        # Create folder for this month
        month_folder = self.vault_path / datetime.now().strftime("%Y-%m %B")
        month_folder.mkdir(exist_ok=True)
        
        # Create cleaner filename
        # Just use the channel name and date, no weird underscores
        safe_channel_name = re.sub(r'[^\w\s-]', '', channel_name).strip().replace(' ', ' ')
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = month_folder / f"{safe_channel_name} - {date_str}.md"
        
        # Build the note content
        content = f"""---
channel: "{channel_name}"
archived: {datetime.now().isoformat()}
date: {datetime.now().strftime("%Y-%m-%d")}
message_count: {len(messages)}
date_range: "{date_range}"
tags: [slack-archive, {safe_channel_name.lower().replace(' ', '-')}]
---

# {channel_name}

*Archived {datetime.now().strftime("%B %d, %Y")} • {len(messages)} messages • Messages from {date_range}*

---

"""
        
        # Add AI Notes if available
        if ai_summary:
            content += f"""{ai_summary}

---

"""
        else:
            # If no AI, add simple placeholder
            content += """## 🔗 Links & Resources
*No AI summary available*

## 📌 Key Points
*No AI summary available*

---

"""
        
        # Add formatted messages in a collapsible section
        formatted_msgs = self.format_messages_markdown(messages)
        
        # Use Obsidian's callout syntax for collapsible sections
        content += """## 💬 Full Conversation

> [!note]- Click to expand full message history
> 
"""
        # Add each line with > prefix for the callout
        for line in formatted_msgs.split('\n'):
            if line:
                content += f"> {line}\n"
            else:
                content += ">\n"
        
        # Optionally add raw text in a collapsed section
        if raw_text:
            # Clean emojis from raw text
            cleaned_raw = re.sub(r':[^:\s]+:', '', raw_text)
            content += """

---

> [!info]- 📄 Raw Text (click to expand)
> ```
"""
            for line in cleaned_raw.split('\n'):
                content += f"> {line}\n"
            content += "> ```"
        
        # Save the file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"   ✅ Saved to: {filename.relative_to(OBSIDIAN_VAULT)}")
        
        # Update index
        self.update_index(channel_name, filename)
        
        return filename
    
    def update_index(self, channel_name, filepath):
        """Update the master index file."""
        index_file = self.vault_path / "INDEX.md"
        
        # Create or load index
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = """# 📚 Slack Archives Index

## Quick Stats
- **Last Updated**: {date}
- **Total Archives**: {count}

## Archives by Channel
"""
        
        # Update content
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Add new entry
        entry = f"- [[{filepath.stem}]] - {channel_name} - {date_str}"
        
        # Find or create channel section
        if f"### {channel_name}" not in content:
            content += f"\n### {channel_name}\n"
        
        # Add entry under channel
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if f"### {channel_name}" in line:
                # Insert after this line
                lines.insert(i + 1, entry)
                break
        else:
            # Just append if section not found
            lines.append(entry)
            
        content = '\n'.join(lines)
        
        # Update stats
        content = content.replace("{date}", date_str)
        archive_count = content.count("[[")
        content = content.replace("{count}", str(archive_count))
        
        # Save
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"   ✅ Updated index")
    
    def process_file(self, filepath, channel_name=None):
        """Process a single text file."""
        print(f"\n📂 Processing: {filepath}")
        
        # Read the file
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        # Get channel name from filename if not provided
        if not channel_name:
            channel_name = Path(filepath).stem.replace('_', ' ').replace('-', ' ').title()
            
        print(f"   Channel: {channel_name}")
        
        # Parse messages
        messages = self.parse_slack_text(raw_text, channel_name)
        print(f"   📝 Parsed {len(messages)} messages")
        
        # Create AI summary
        ai_summary = self.create_ai_summary(messages, channel_name)
        
        # Save to Obsidian
        self.save_to_obsidian(channel_name, messages, ai_summary, raw_text)
        
        return True
    
    def process_folder(self, folder_path):
        """Process all .txt files in a folder."""
        folder = Path(folder_path)
        txt_files = list(folder.glob("*.txt"))
        
        print(f"\n📁 Found {len(txt_files)} text files to process")
        
        for filepath in txt_files:
            try:
                self.process_file(filepath)
                print(f"   ✅ Completed: {filepath.name}")
            except Exception as e:
                print(f"   ❌ Error with {filepath.name}: {e}")
                
        print(f"\n✨ Processed {len(txt_files)} files!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Slack Auto Notes - Transform Slack copies into Obsidian gold ✨')
    parser.add_argument('-f', '--file', help='Path to a single text file')
    parser.add_argument('-d', '--directory', help='Path to directory with text files')
    parser.add_argument('-c', '--channel', help='Channel/DM name (optional)')
    
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                      Slack Auto Notes                        ║
║         Transform Slack copies into Obsidian gold ✨         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    vibe = NotesVibe()
    
    # Handle command line arguments
    if args.file:
        vibe.process_file(args.file, args.channel)
        print(f"\n✅ Done! Check your Obsidian vault: {OBSIDIAN_VAULT / 'Slack Archives'}")
        return
    elif args.directory:
        vibe.process_folder(args.directory)
        print(f"\n✅ Done! Check your Obsidian vault: {OBSIDIAN_VAULT / 'Slack Archives'}")
        return
    
    # Interactive mode
    print("How do you want to provide the Slack text?")
    print("1. Single text file")
    print("2. Folder with multiple text files")
    
    choice = input("\nChoice (1-2): ").strip()
    
    if choice == "1":
        filepath = input("Enter path to text file: ").strip()
        channel = input("Channel/DM name (or press Enter to auto-detect): ").strip()
        vibe.process_file(filepath, channel if channel else None)
        
    elif choice == "2":
        folder = input("Enter folder path: ").strip()
        vibe.process_folder(folder)
    else:
        print("Invalid choice. Please run again and select 1 or 2.")
        return
        
    print(f"\n✅ Done! Check your Obsidian vault: {OBSIDIAN_VAULT / 'Slack Archives'}")


if __name__ == "__main__":
    main()