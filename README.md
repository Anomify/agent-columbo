# Agent Columbo

**Agent Columbo** is Anomify's open-source, interactive debugging detective.

It runs on your machine, allows you to submit queries in natural language, and investigates them by issuing local diagnostic commands, securely sharing only the information **you approve** with our server to help analyse and solve issues.

Columbo does **not** make any changes to your system - it just performs read-only inspection commands that you explicitly allow.

---

## Why Columbo?

Modern systems are complex. Diagnosing failures, configuration issues, and subtle security problems often requires both local access *and* expert analysis. Columbo bridges that gap:

* The service knows how to interrogate UNIX-like systems, logs, and common applications.
* The local Detective client collaborates with the Columbo service on our servers to interpret what it finds.
* The client always asks you before running a command.
* The client always asks you before sending any output.
* You stay fully in control.

We built Columbo because we wanted a debugging assistant that was powerful but also **transparent, predictable, and respectful of user privacy**.

We at Anomify use it all the time.

---

## Full User Control & Transparency

The Columbo client is deliberately designed so **you can see everything it does**:

* **No silent commands.** Every command is shown to you and must be approved.
* **No background data collection.** Nothing is sent unless you confirm it.
* **No configuration surprises.** The config file is small, explicit, and easy to audit.
* **No elevated privileges needed.** Columbo *does not* require `sudo`, and we recommend not allowing this unless you explicitly need it.

You're encouraged to read the client code (this repository) before using it. The logic is intentionally simple and auditable.

---

## Privacy & Data Handling

Columbo stores a conversation transcript on the server **only for the duration of the investigation** so that it can provide coherent guidance.

* Sessions automatically expire and are deleted after **24 hours of inactivity**.
* You can manually delete a conversation at any time using
  `/delete {conversation_id}`
  *(this feature is currently being finalised)*.
* Data is **never** shared, aggregated, analysed, or used for any purpose outside your investigation.

Your diagnostic data is **your property** and you remain in control.

---

## Getting Started

Agent Columbo is currently in **private beta**.

To request an API token, please contact us via [the contact form on our website](https://anomify.ai/contact).

### Installation

```bash
git clone https://github.com/Anomify/agent-columbo.git
cd agent-columbo
pip install .
```

### Basic Usage

The simplest example (also in `examples/demo.py`):

```python
from columbo.detective import Detective
import yaml

if __name__ == '__main__':

    with open('./config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    detective = Detective(config)
    detective.on_duty()
```

When running, Columbo will prompt you:

1. **"What would you like me to investigate?"**
2. It proposes commands and asks **permission** before running them.
3. It shows the output and asks **permission** before sending it.

---

## Configuration

`config.yaml` controls Columbo's behaviour:

```yaml
server_base_url: https://columbo.anomify.ai/api/v1
api_token: YOUR_ANOMIFY_API_TOKEN_GOES_HERE

settings:
  allow_sudo: false
  review_commands_before_executing: true
  review_command_output_before_sending: true
  command_max_output_size: 20000
```

**Settings Explained:**

* `allow_sudo`:
  Whether Columbo may run `sudo` commands. Default `false`.
* `review_commands_before_executing`:
  Shows each command for approval before running.
* `review_command_output_before_sending`:
  Shows the output so you can allow or decline to send it.
* `command_max_output_size`:
  Protects you from accidentally sending enormous logs.

---

## Example Use Cases

Columbo excels when the root cause isn't obvious, or if you're not an experienced coder or system administrator. Some examples:

* "Have there been any failed SSH logins this week?"
* "Is my system low on disk space?"
* "Are there any glaring security misconfigurations?"
* "What's preventing this service from starting?"
* "Can you have a look at my new app in /home/danziger/apps/frank and tell me if there are any issues?"

Because Columbo can execute on your local machine - with your supervision - it can provide far more accurate diagnostics than remote-only tools.

---

## How It Works

1. **You describe an issue.**
2. The Detective client asks Columbo HQ (our server) how best to investigate.
3. The server proposes a command.
4. You approve or decline to run that command.
5. You preview the output; if you approve, it's sent back.
6. Columbo HQ analyses the result and proposes the next step.

This continues until the case is **closed**.

The client code is open source, intentionally short, and avoids unnecessary complexity so that you can audit every action it performs.

---

## Licence

This project is released under **CC BY-NC-SA 4.0**
See the licence: [https://creativecommons.org/licenses/by-nc-sa/4.0/](https://creativecommons.org/licenses/by-nc-sa/4.0/)

---

## Feedback

We'd love your feedback during the beta.
Please contact us via [the contact form on our website](https://anomify.ai/contact) with comments, questions or ideas.

