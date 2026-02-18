import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class DecorationProvider {
	private warningDecorationType: vscode.TextEditorDecorationType;
	private successDecorationType: vscode.TextEditorDecorationType;
	private infoDecorationType: vscode.TextEditorDecorationType;

	constructor(private client: MembriaClient) {
		// Warning decoration (red squiggly underline)
		this.warningDecorationType = vscode.window.createTextEditorDecorationType({
			backgroundColor: 'rgba(255, 0, 0, 0.1)',
			borderColor: 'rgba(255, 0, 0, 0.5)',
			borderStyle: 'solid',
			borderWidth: '1px',
			cursor: 'pointer'
		});

		// Success decoration (green)
		this.successDecorationType = vscode.window.createTextEditorDecorationType({
			backgroundColor: 'rgba(0, 128, 0, 0.1)',
			borderColor: 'rgba(0, 128, 0, 0.5)',
			borderStyle: 'solid',
			borderWidth: '1px'
		});

		// Info decoration (blue)
		this.infoDecorationType = vscode.window.createTextEditorDecorationType({
			backgroundColor: 'rgba(0, 0, 255, 0.1)',
			borderColor: 'rgba(0, 0, 255, 0.5)',
			borderStyle: 'solid',
			borderWidth: '1px'
		});
	}

	async updateDecorations(editor: vscode.TextEditor): Promise<void> {
		const text = editor.document.getText();
		const warnings: vscode.DecorationOptions[] = [];
		const successes: vscode.DecorationOptions[] = [];
		const infos: vscode.DecorationOptions[] = [];

		// Scan document for decision-related patterns
		const lines = editor.document.getText().split('\n');

		for (let i = 0; i < lines.length; i++) {
			const line = lines[i];

			// Check for decision patterns
			if (this.isDecisionLine(line)) {
				try {
					const context = await this.client.getContext(line, 'vscode', 0.7);

					const range = new vscode.Range(i, 0, i, line.length);

					if (context && context.warnings && context.warnings.length > 0) {
						warnings.push({
							range,
							hoverMessage: new vscode.MarkdownString(
								`⚠️ **Warning:** ${context.warnings[0]}`
							)
						});
					} else if (context && context.calibration) {
						const gap = context.calibration.confidence_gap;
						if (Math.abs(gap) > 0.1) {
							infos.push({
								range,
								hoverMessage: new vscode.MarkdownString(
									`📊 **Calibration Info:** Confidence gap is ${(gap * 100).toFixed(1)}%`
								)
							});
						} else {
							successes.push({
								range,
								hoverMessage: new vscode.MarkdownString(
									`✅ **Good Signal:** Success rate ${(context.calibration.mean_success_rate * 100).toFixed(1)}%`
								)
							});
						}
					}
				} catch (error) {
					// Continue on error
				}
			}
		}

		editor.setDecorations(this.warningDecorationType, warnings);
		editor.setDecorations(this.successDecorationType, successes);
		editor.setDecorations(this.infoDecorationType, infos);
	}

	private isDecisionLine(line: string): boolean {
		// Simple heuristics to detect decision-related lines
		const patterns = [
			/use\s+\w+/i,
			/implement\s+\w+/i,
			/adopt\s+\w+/i,
			/choose\s+\w+/i,
			/decide\s+to/i,
			/should\s+\w+/i,
			/\bcache\b/i,
			/\bdatabase\b/i,
			/\bauth/i,
			/\bapi\b/i
		];

		return patterns.some(pattern => pattern.test(line));
	}

	dispose(): void {
		this.warningDecorationType.dispose();
		this.successDecorationType.dispose();
		this.infoDecorationType.dispose();
	}
}

export function registerDecorationProvider(
	context: vscode.ExtensionContext,
	client: MembriaClient
): DecorationProvider {
	const decorationProvider = new DecorationProvider(client);

	// Update decorations on document change
	context.subscriptions.push(
		vscode.workspace.onDidChangeTextDocument(async (event) => {
			const editor = vscode.window.activeTextEditor;
			if (editor && editor.document === event.document) {
				// Debounce updates
				await decorationProvider.updateDecorations(editor);
			}
		})
	);

	// Update decorations when editor changes
	context.subscriptions.push(
		vscode.window.onDidChangeActiveTextEditor(async (editor) => {
			if (editor) {
				await decorationProvider.updateDecorations(editor);
			}
		})
	);

	// Initial update
	if (vscode.window.activeTextEditor) {
		decorationProvider.updateDecorations(vscode.window.activeTextEditor);
	}

	context.subscriptions.push(decorationProvider);

	return decorationProvider;
}
