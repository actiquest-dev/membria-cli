import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class MemberiaHoverProvider implements vscode.HoverProvider {
	constructor(private client: MembriaClient) {}

	async provideHover(
		document: vscode.TextDocument,
		position: vscode.Position,
		token: vscode.CancellationToken
	): Promise<vscode.Hover | undefined> {
		// Get word at cursor
		const wordRange = document.getWordRangeAtPosition(position);
		if (!wordRange) {
			return undefined;
		}

		const word = document.getText(wordRange);

		// Get line context for better understanding
		const line = document.lineAt(position).text;

		try {
			// Try to get context from Membria
			const context = await this.client.getContext(line, 'vscode', 0.7);

			if (!context || Object.keys(context).length === 0) {
				return undefined;
			}

			// Build markdown content
			const markdown = new vscode.MarkdownString();
			markdown.appendMarkdown('### 📋 Membria Context\n\n');

			if (context.statement) {
				markdown.appendMarkdown(`**Statement:** ${context.statement}\n\n`);
			}

			if (context.calibration) {
				markdown.appendMarkdown('**Calibration:**\n\n');
				markdown.appendMarkdown(
					`- Success Rate: ${(context.calibration.mean_success_rate * 100).toFixed(1)}%\n`
				);
				markdown.appendMarkdown(
					`- Confidence Gap: ${(context.calibration.confidence_gap * 100).toFixed(1)}%\n`
				);
				markdown.appendMarkdown(`- Sample Size: ${context.calibration.sample_size}\n\n`);
			}

			if (context.recent_outcomes && context.recent_outcomes.length > 0) {
				markdown.appendMarkdown('**Recent Outcomes:**\n\n');
				context.recent_outcomes.slice(0, 3).forEach((outcome: any) => {
					markdown.appendMarkdown(`- ${outcome.status} (${outcome.score})\n`);
				});
				markdown.appendMarkdown('\n');
			}

			if (context.warnings && context.warnings.length > 0) {
				markdown.appendMarkdown('⚠️ **Warnings:**\n\n');
				context.warnings.slice(0, 2).forEach((warning: string) => {
					markdown.appendMarkdown(`- ${warning}\n`);
				});
			}

			markdown.isTrusted = true;
			return new vscode.Hover(markdown);
		} catch (error) {
			// Silently fail on hover to not disrupt user experience
			return undefined;
		}
	}
}

export function registerHoverProviders(
	context: vscode.ExtensionContext,
	client: MembriaClient
): void {
	const hoverProvider = new MemberiaHoverProvider(client);

	// Register for Python files
	context.subscriptions.push(
		vscode.languages.registerHoverProvider('python', hoverProvider)
	);

	// Register for TypeScript files
	context.subscriptions.push(
		vscode.languages.registerHoverProvider('typescript', hoverProvider)
	);

	// Register for JavaScript files
	context.subscriptions.push(
		vscode.languages.registerHoverProvider('javascript', hoverProvider)
	);
}
