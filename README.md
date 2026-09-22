# 🤖 AI Assistant for Odoo 18

> **Provider-Agnostic AI Assistant** — An intelligent AI assistant seamlessly integrated with Odoo.  
> Supports OpenAI, Google Gemini, Anthropic Claude, and Self-Hosted Models (Ollama, vLLM, Qwen).

| | |
|---|---|
| **Version** | `1.0.0` |
| **Category** | Productivity |
| **License** | LGPL-3 |
| **Depends** | `base`, `mail` |
| **Odoo** | 18.0 |

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Supported Providers](#-supported-providers)
- [Tool Calling System](#-tool-calling-system)
- [Security Model](#-security-model)
- [Module Structure](#-module-structure)
- [Usage](#-usage)
- [Contributing](#-contributing)

---

## 🌟 Overview

**AI Assistant** is an Odoo module built on a **Provider-Agnostic Architecture**, allowing you to switch AI providers at any time without changing code—simply configure them via the Settings page.

This module integrates directly with **Odoo Discuss** — users can talk to the AI through the familiar chat interface, and the AI can autonomously **search, create, and manage data** within Odoo via its advanced Tool Calling (Function Calling) mechanism.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔀 **Multi-Provider & Role-based Routing** | Switch between OpenAI, Gemini, Claude, and Ollama instantly. Assign specific providers for Write, Read, or Vision tasks. |
| 💬 **Discuss Integration** | Chat with the AI via Direct Message or `@mention` in any channel. |
| 🧠 **Conversation Memory** | AI remembers the conversation history (configurable limit via Settings). |
| 🔧 **Tool Calling (Function Calling)** | AI autonomously calls Odoo API to read and write data. |
| 🔔 **Proactive Notifications** | Set up rules for the AI to proactively monitor Odoo data (e.g., unpaid invoices) and notify users on a schedule. |
| 🛡️ **4-Layer Security** | Prevents unauthorized access to sensitive data and blacklisted models. |
| ✨ **Systray Widget** | A Magic Wand icon on the Systray for quick access to the chat. |
| ⚙️ **Dynamic Settings** | Configure limits, prompts, and access controls via the Odoo Settings UI. |

---

## 🏗 Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    Odoo Discuss UI                      │
│              (Chat / DM / @mention)                     │
└──────────────────────┬──────────────────────────────────┘
                       │ message_post()
                       ▼
┌──────────────────────────────────────────────────────────┐
│               discuss.channel (Override)                 │
│         Intercept messages → Build context               │
│         Memory: Managed by dynamic config                │
└──────────────────────┬───────────────────────────────────┘
                       │ chat(messages)
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   ai.engine (Router)                     │
│         Route → Adapter based on protocol_type           │
│         Agentic Loop (configurable turns)                │
│         System Prompt Injection (Base + Custom)          │
└───────┬──────────────┼──────────────┬────────────────────┘
        │              │              │
        ▼              ▼              ▼
┌──────────────┐┌──────────────┐┌──────────────┐
│ai.adapter    ││ai.adapter    ││ai.adapter    │
│  .openai     ││  .gemini     ││  .anthropic  │
│              ││              ││              │
│OpenAI / Qwen ││Google Gemini ││Claude        │
│DeepSeek      ││              ││              │
│Ollama / vLLM ││              ││              │
└──────────────┘└──────────────┘└──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │ Tool Calls
                       ▼
┌──────────────────────────────────────────────────────────┐
│              ai.tools.executor (Security)                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Layer 1: System Blacklist (ir.*, res.users, ...)    │ │
│  │ Layer 2: Odoo RBAC (Native access rights)           │ │
│  │ Layer 3: In-Flight Sanitization (password, token)   │ │
│  │ Layer 4: Error Sanitization (hide server paths)     │ │
│  └─────────────────────────────────────────────────────┘ │
│              ↕ search_read / fields_get / create         │
│                       Odoo ORM                           │
└──────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

- **Odoo 18.0** (Community or Enterprise)
- Python package: `requests`
- At least one AI Provider API Key (or a local instance like Ollama)

### Steps

1. **Copy the module** to your Odoo addons directory:

   ```bash
   cp -r ai_assistant /path/to/odoo/addons/
   ```

2. **Update Apps List** in Odoo:

   ```text
   Settings → General Settings → Developer Tools → Update Apps List
   ```

3. **Search and Install** the `AI Assistant` module from the Apps menu.

4. The module will **automatically create an AI User** (`ai_assistant`) via the `post_init_hook` — no extra setup needed.

---

## ⚙ Configuration

### 1. Add AI Providers

Navigate to **AI Assistant → Configuration → AI Providers** and create a new Provider:

| Field | Description | Example |
|---|---|---|
| **Provider Name** | Display name | `GPT-4o`, `Gemini Pro`, `Qwen Local` |
| **Protocol Type** | Connection protocol | `OpenAI Compatible` / `Google Gemini Native` / `Anthropic Claude Native` |
| **Base URL** | API URL (leave empty for default) | `http://localhost:11434/v1` |
| **API Key** | Authentication key | `sk-...` |
| **Model Name** | The exact model name | `gpt-4o`, `gemini-1.5-pro`, `qwen-max` |
| **Role** | The AI's responsibility | `Read & General Chat` / `Write` / `Vision` |
| **Active** | Enable this provider (Only 1 active per role) | ✅ |

### 2. General Settings

Navigate to **Settings → AI Assistant** to configure dynamic settings:

| Setting | Description |
|---|---|
| **Custom System Prompt** | Append your own business rules or persona to the AI's base prompt. |
| **Max History Messages** | Number of previous messages the AI can remember. |
| **Max Tool Execution Turns** | Maximum number of iterative tool calls the AI can make per request. |
| **Enable AI Create/Update/Delete Actions** | Explicitly grant the AI permission to modify Odoo records. |
| **Write Action Keywords** | Comma-separated trigger words (e.g., "create,update,delete,สร้าง") that route the request to the Write Provider. |

### 3. Proactive Notifications

Navigate to **AI Assistant → Configuration → Notification Rules** to set up scheduled AI checks. For example, you can tell the AI:
*"Check if there are any unpaid customer invoices older than 15 days, and if so, summarize them."*
The AI will run on a cron schedule and send you a direct message if the condition is met.

---

## 🔌 Supported Providers

### OpenAI Compatible Protocol

Works with any service that supports the OpenAI Chat Completions API:

| Service | Base URL | Example Models |
|---|---|---|
| **OpenAI** | *(Leave empty)* | `gpt-4o`, `gpt-4o-mini` |
| **Qwen (DashScope)** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max`, `qwen-plus` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` |
| **Ollama** | `http://localhost:11434/v1` | `llama3.1`, `qwen2.5` |
| **vLLM** | `http://localhost:8000/v1` | *(Served model name)* |

### Google Gemini Native

| Field | Value |
|---|---|
| **Protocol Type** | `Google Gemini Native` |
| **Base URL** | *(Leave empty)* |
| **Model Name** | `gemini-1.5-pro`, `gemini-2.0-flash` |

### Anthropic Claude Native

| Field | Value |
|---|---|
| **Protocol Type** | `Anthropic Claude Native` |
| **Base URL** | *(Leave empty)* |
| **Model Name** | `claude-3-5-sonnet-20240620`, `claude-3-opus-20240229` |

---

## 🔧 Tool Calling System

The AI can interact with the Odoo ORM automatically via **Function Calling**:

### Read Tools (Always Enabled)

| Tool | Description | Example Usage |
|---|---|---|
| `search_records` | Search records from any model | *"Show me all corporate customers"* |
| `get_fields` | Inspect a model's fields | *"What fields does res.partner have?"* |
| `aggregate_records` | GROUP BY and SUM/COUNT/AVG | *"Summarize sales by customer"* |

### Write Tools (Requires Settings Approval)

| Tool | Description | Example Usage |
|---|---|---|
| `create_record` | Create a new record | *"Create a new company named ABC Corp"* |
| `update_record` | Edit an existing record | *"Change the name of contact ID 5 to Jane"* |
| `delete_record` | Delete a record | *"Delete contact ID 12"* |

### Agentic Loop

The AI Engine operates on an **Agentic Loop** (up to the configured Max Turns)—meaning the AI can:
1. Call `get_fields` to understand a model's structure.
2. Formulate a correct domain based on existing fields.
3. Call `search_records`.
4. Summarize the results for the user.
All of this happens **automatically** behind the scenes.

---

## 🛡 Security Model

The module utilizes a strict **4-Layer Security Model**:

### Layer 1 — System Model Blacklist
Blocks access to sensitive system models:
```python
BLOCKED = ['ir.*', 'res.users', 'res.groups', 'res.config.settings', 'ir.config_parameter']
```

### Layer 2 — Odoo Native RBAC
The AI operates under the standard `base.group_user` rights. If a record requires higher privileges, the AI receives an `AccessError`.

### Layer 3 — In-Flight Data Sanitization
Fields containing sensitive keywords are stripped from results before reaching the AI:
```python
SENSITIVE_MARKERS = ['password', 'secret', 'token', 'api_key', 'otp', 'pin', 'session']
```

### Layer 4 — Error Sanitization
Server paths and internal exception details are obfuscated to prevent information leakage.

---

## 📂 Module Structure

```text
ai_assistant/
├── __manifest__.py                  # Module metadata & dependencies
├── __init__.py                      # Package init
├── hooks.py                         # post_init_hook: Auto-creates AI User
│
├── models/
│   ├── ai_engine.py                 # Core Router & Agentic Loop
│   ├── ai_provider.py               # Provider Configurations
│   ├── ai_adapter_openai.py         # OpenAI Compatible Adapter
│   ├── ai_adapter_gemini.py         # Google Gemini Native Adapter
│   ├── ai_adapter_anthropic.py      # Anthropic Claude Native Adapter
│   ├── ai_tools_schema.py           # Function Calling JSON Schemas
│   ├── ai_tools_executor.py         # Tool Executor & Security Layer
│   ├── ai_notification_rule.py      # Proactive Notification Rules logic
│   ├── ai_prompt_template.py        # System Prompt Templates
│   ├── discuss_channel.py           # Discuss Integration & Memory
│   └── res_config_settings.py       # Dynamic Settings
│
├── views/
│   ├── ai_provider_views.xml        # Provider List & Form views
│   ├── ai_notification_rule_views.xml # Notification Rules UI
│   ├── res_config_settings_views.xml  # Settings UI
│   └── menuitems.xml                # Top-level menu structure
│
├── data/
│   ├── ai_prompt_template_data.xml  # Base prompt templates
│   └── ai_notification_cron.xml     # Scheduled Action for notifications
│
├── security/
│   ├── ir.model.access.csv          # ACL: Admin=CRUD, User=Read-only
│   └── ir_rule.xml                  # Multi-company / User record rules
│
├── static/src/components/
│   └── floating_widget/             # OWL Systray Widget
│
└── tests/
    ├── test_ai_provider.py          # Validation & Constraint tests
    ├── test_ai_engine.py            # Routing & Prompt Injection tests
    └── test_ai_tools_executor.py    # Security & Sanitization tests
```

---

## 💬 Usage

### Method 1: Direct Message (DM)
1. Open **Discuss**.
2. Create a Direct Message with **AI Assistant**.
3. Type your request in plain English (or your preferred language).

### Method 2: @mention in Channels
1. Open any channel in Discuss.
2. Invite **AI Assistant** to the channel.
3. Type `@AI Assistant` followed by your request.

### Method 3: Systray Icon
1. Click the 🪄 (Magic Wand) icon on the top right Systray.
2. The Discuss chat window will open automatically.

### Example Prompts
```text
🗣️ "Show me all corporate customers"
🗣️ "What fields does res.partner have?"
🗣️ "Search for Sale Orders with a total value greater than $10,000"
🗣️ "Create a new contact named John Doe with email john@example.com"
```

---

## 🤝 Contributing

Pull Requests and Issue Reports are welcome!

1. **Fork** this repository.
2. Create a **feature branch** (`git checkout -b feature/my-feature`).
3. **Commit** your changes (`git commit -m 'feat: add my feature'`).
4. **Push** to the branch (`git push origin feature/my-feature`).
5. Open a **Pull Request**.

### Coding Standards
- Strictly adhere to the [Odoo Coding Guidelines](https://www.odoo.com/documentation/18.0/contributing/development/coding_guidelines.html).
- Add docstrings for every new method.
- Add test coverage (`tests/`) for all core business logic and security rules.
- Maintain appropriate access rights for any new models.

---

<p align="center">
  <b>Made with ❤️ for the Odoo Community</b>
</p>
