# Contributing

We love contributions! Here's how you can help make Zero Ichi better.

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
2.  Make your changes.
3.  **Format and Lint** your code:
    ```bash
    uv run ruff format .
    uv run ruff check .
    ```
    > [!IMPORTANT]
    > CI will fail if code is not formatted or has lint errors.

4.  **Test** your changes locally.

## Project Structure

See [Architecture](/development/architecture) for a deep dive.

-   `commands/`: Add new commands here.
-   `core/`: Core logic (avoid touching unless necessary).
-   `locales/`: Update these for text changes.

## Pull Requests

-   Keep PRs focused on a single feature or fix.
-   Use clear, descriptive titles.
-   Describe what you changed and why.
-   If you added a feature, include a screenshot or usage example.

## Adding Translations

We use JSON files in `locales/` for i18n.

1.  Copy `locales/en.json` to `locales/<code>.json`.
2.  Update `_meta.label` with the language name.
3.  Translate the values.
4.  Submit a PR!

## Reporting Bugs

Please use the [GitHub Issues](https://github.com/MhankBarBar/zero-ichi/issues) to report bugs. Include:
-   Steps to reproduce
-   Expected vs actual behavior
-   Logs or screenshots
