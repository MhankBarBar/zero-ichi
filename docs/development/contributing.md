# Contributing

Contributions are welcome. Here's how to get started.

## Getting Started

1.  **Fork** the repository
2.  **Clone** your fork:
    ```bash
    git clone https://github.com/your-username/zero-ichi
    cd zero-ichi
    ```
3.  **Install dependencies**:
    ```bash
    pip install uv
    uv sync
    ```

## Development Workflow

1.  Create a new branch for your feature or fix:
    ```bash
    git checkout -b feature/my-cool-feature
    ```
2.  Make your changes. All source code lives under `src/`.
3.  **Format and Lint** your code:
    ```bash
    uv run ruff format .
    uv run ruff check .
    ```
    > [!IMPORTANT]
    > CI will fail if code is not formatted or has lint errors.

4.  **Run the bot** to test your changes:
    ```bash
    uv run zero-ichi
    ```
    The bot supports auto-reload — file changes are picked up without restarting.

## Project Structure

See [Architecture](/development/architecture) for a full breakdown.

-   `src/commands/` — Add new commands here.
-   `src/core/` — Core logic (client, middleware, logger, etc.).
-   `src/ai/` — AI agent, context, memory, and tools.
-   `src/locales/` — Translation JSON files.
-   `src/config/` — Static settings loaded from `config.json`.

## Pull Requests

-   Keep PRs focused on a single feature or fix.
-   Use clear, descriptive titles.
-   Describe what you changed and why.
-   If you added a feature, include a screenshot or usage example.

## Adding a Command

Create a new file in the appropriate `src/commands/<category>/` directory:

```python
from core.command import Command

class MyCommand(Command):
    name = "mycommand"
    description = "Does something cool"
    usage = "/mycommand <arg>"

    async def execute(self, msg, bot, args, prefix):
        await bot.reply(msg, "Hello!")
```

Commands are auto-discovered — no registration needed.

## Adding Translations

Translation files live in `src/locales/`.

1.  Copy `src/locales/en.json` to `src/locales/<code>.json`.
2.  Update `_meta.label` with the language name.
3.  Translate the values.
4.  Submit a PR.

## Reporting Bugs

Please use [GitHub Issues](https://github.com/MhankBarBar/zero-ichi/issues) to report bugs. Include:
-   Steps to reproduce
-   Expected vs actual behavior
-   Logs or screenshots
