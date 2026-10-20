# spython Language Support

Syntax highlighting, editing support, snippets, and a command for running
`.spy` files in VS Code.

## Development

1. Open this `vscode-extension` folder in VS Code.
2. Run `npm install` and then `npm run compile` in its terminal.
3. Press `F5` to open an Extension Development Host.
4. Open a `.spy` file and run **Spython: Run Spython File** from the Command
   Palette.

The runner looks for `spython.py` in the file's workspace folder, then next to
the extension project. Set `spython.pythonCommand` if your Python executable is
not named `python3`.

## Features

- `.spy` language recognition, syntax coloring, bracket matching, and comments
- Snippets for functions, conditionals, loops, and printing
- **Spython: Run Spython File**, with output shown in the `spython` output
  channel