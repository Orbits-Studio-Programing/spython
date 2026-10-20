import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel("spython");
  context.subscriptions.push(output);

  context.subscriptions.push(
    vscode.commands.registerCommand("spython.runFile", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || editor.document.isUntitled) {
        vscode.window.showErrorMessage("Open a saved .spy file before running it.");
        return;
      }

      if (!(await editor.document.save())) {
        return;
      }

      const workspaceFolder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
      const workspaceRuntime = workspaceFolder
        ? await vscode.workspace.findFiles(
            new vscode.RelativePattern(workspaceFolder, "spython.py"),
            "**/node_modules/**",
            1,
          )
        : [];
      const runtimePath =
        workspaceRuntime[0]?.fsPath ?? join(dirname(context.extensionPath), "spython.py");

      if (!existsSync(runtimePath)) {
        vscode.window.showErrorMessage(
          "Could not find spython.py. Open the spython project folder containing the interpreter.",
        );
        return;
      }

      const pythonCommand = vscode.workspace
        .getConfiguration("spython")
        .get<string>("pythonCommand", "python3");
      const workingDirectory = workspaceFolder?.uri.fsPath ?? dirname(runtimePath);

      output.clear();
      output.appendLine(`Running ${editor.document.fileName}`);
      output.show(true);

      const process = spawn(
        pythonCommand,
        [runtimePath, editor.document.uri.fsPath],
        { cwd: workingDirectory },
      );
      process.stdout.on("data", (data: Buffer) => output.append(data.toString()));
      process.stderr.on("data", (data: Buffer) => output.append(data.toString()));
      process.on("error", (error: Error) => {
        output.appendLine(error.message);
        vscode.window.showErrorMessage(`Could not start ${pythonCommand}: ${error.message}`);
      });
      process.on("close", (code: number | null) => {
        output.appendLine(`Process exited with code ${code ?? "unknown"}.`);
      });
    }),
  );
}

export function deactivate(): void {}