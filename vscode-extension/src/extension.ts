import * as vscode from 'vscode';
import { ChatProvider } from './providers/chatProvider';
import { MembriaClient } from './membriaMCPClient';
import { MemberiaHoverProvider, registerHoverProviders } from './providers/hoverProvider';
import { DecorationProvider, registerDecorationProvider } from './providers/decorationProvider';

let client: MembriaClient;

export function activate(context: vscode.ExtensionContext) {
	console.log('Membria extension activating...');

	// Initialize Membria MCP client
	client = new MembriaClient();

	// Register tree data providers (Removed for CLI-first approach)
	
	// Register Chat Provider
	const chatProvider = new ChatProvider(client, context.extensionUri);
	context.subscriptions.push(
		vscode.window.registerWebviewViewProvider(ChatProvider.viewType, chatProvider)
	);

	// Register hover provider
	registerHoverProviders(context, client);

	// Register decoration provider
	registerDecorationProvider(context, client);

	// Register commands
	registerCommands(context, client);

	console.log('Membria extension activated successfully');
}

function registerCommands(
	context: vscode.ExtensionContext,
	client: MembriaClient
) {
	// Capture Decision
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.captureDecision', async () => {
			const statement = await vscode.window.showInputBox({
				prompt: 'What decision are you making?',
				placeHolder: 'e.g., Use PostgreSQL for user database'
			});

			if (!statement) return;

			const alternatives = await vscode.window.showInputBox({
				prompt: 'Alternative options (comma-separated)',
				placeHolder: 'e.g., MongoDB, MySQL, DynamoDB'
			});

			const confidence = await vscode.window.showInputBox({
				prompt: 'Your confidence level (0-1)',
				placeHolder: '0.8',
				validateInput: (value) => {
					const num = parseFloat(value);
					return num >= 0 && num <= 1 ? '' : 'Enter a number between 0 and 1';
				}
			});

			if (!confidence) return;

			try {
				const result = await client.captureDecision(
					statement,
					alternatives?.split(',').map(a => a.trim()) || [],
					parseFloat(confidence)
				);

				vscode.window.showInformationMessage(`Decision captured: ${result.decision_id}`);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to capture decision: ${error}`);
			}
		})
	);

	// Get Context
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.getContext', async () => {
			const statement = await vscode.window.showInputBox({
				prompt: 'What decision context do you need?',
				placeHolder: 'e.g., Use JWT for authentication'
			});

			if (!statement) return;

			try {
				const context_result = await client.getContext(statement);
				const panel = vscode.window.createWebviewPanel(
					'membriaContext',
					'Decision Context',
					vscode.ViewColumn.Beside,
					{}
				);

				panel.webview.html = getContextWebviewContent(context_result);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to get context: ${error}`);
			}
		})
	);

	// Validate Plan
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.validatePlan', async () => {
			const planText = await vscode.window.showInputBox({
				prompt: 'Describe your plan steps',
				placeHolder: 'Step 1: ...\nStep 2: ...',
				ignoreFocusOut: true
			});

			if (!planText) return;

			const steps = planText.split('\n').filter(s => s.trim());

			try {
				const validation = await client.validatePlan(steps);
				const panel = vscode.window.createWebviewPanel(
					'membriaValidation',
					'Plan Validation',
					vscode.ViewColumn.Beside,
					{}
				);

				panel.webview.html = getValidationWebviewContent(validation);

				if (validation.high_severity > 0) {
					vscode.window.showWarningMessage(`⚠️ ${validation.high_severity} high severity issues in plan`);
				} else {
					vscode.window.showInformationMessage('✅ Plan looks good!');
				}
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to validate plan: ${error}`);
			}
		})
	);

	// Show Plans
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.showPlans', async () => {
			try {
				const plans = await client.listPlans();
				const panel = vscode.window.createWebviewPanel(
					'membriaPlans',
					'Plans',
					vscode.ViewColumn.Beside,
					{}
				);

				panel.webview.html = getPlansWebviewContent(plans);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to show plans: ${error}`);
			}
		})
	);

	// Show Skills
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.showSkills', async () => {
			try {
				const skills = await client.listSkills();
				const panel = vscode.window.createWebviewPanel(
					'membriaSkills',
					'Skills',
					vscode.ViewColumn.Beside,
					{}
				);

				panel.webview.html = getSkillsWebviewContent(skills);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to show skills: ${error}`);
			}
		})
	);

	// Generate Skill
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.generateSkill', async () => {
			const domain = await vscode.window.showQuickPick(
				['database', 'auth', 'api', 'cache', 'messaging', 'storage'],
				{ placeHolder: 'Select domain' }
			);

			if (!domain) return;

			try {
				const result = await client.generateSkill(domain);
				vscode.window.showInformationMessage(`Skill generated: ${result.skill_id}`);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to generate skill: ${error}`);
			}
		})
	);

	// Toggle Panel
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.togglePanel', async () => {
			await vscode.commands.executeCommand('workbench.view.extension.membria-explorer');
		})
	);

	// Record Outcome
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.recordOutcome', async () => {
			const decisionId = await vscode.window.showInputBox({
				prompt: 'Decision ID',
				placeHolder: 'dec_abc123...'
			});

			if (!decisionId) return;

			const status = await vscode.window.showQuickPick(
				['success', 'failure', 'partial'],
				{ placeHolder: 'Outcome status' }
			);

			if (!status) return;

			try {
				const result = await client.recordOutcome(decisionId, status);
				vscode.window.showInformationMessage(`Outcome recorded for ${decisionId}`);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to record outcome: ${error}`);
			}
		})
	);

	// View Calibration
	context.subscriptions.push(
		vscode.commands.registerCommand('membria.viewCalibration', async () => {
			try {
				const calibration = await client.getCalibration();
				const panel = vscode.window.createWebviewPanel(
					'membriaCalibration',
					'Team Calibration',
					vscode.ViewColumn.Beside,
					{}
				);

				panel.webview.html = getCalibrationWebviewContent(calibration);
			} catch (error) {
				vscode.window.showErrorMessage(`Failed to get calibration: ${error}`);
			}
		})
	);
}

function getContextWebviewContent(context: any): string {
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<style>
				body { font-family: var(--vscode-font-family); padding: 20px; }
				.section { margin: 20px 0; }
				.title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
				.content { white-space: pre-wrap; font-size: 13px; }
				.warning { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }
				.success { background: #d4edda; padding: 10px; border-radius: 4px; margin: 10px 0; }
			</style>
		</head>
		<body>
			<div class="section">
				<div class="title">📋 Decision Context</div>
				<div class="content">${JSON.stringify(context, null, 2)}</div>
			</div>
		</body>
		</html>
	`;
}

function getValidationWebviewContent(validation: any): string {
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<style>
				body { font-family: var(--vscode-font-family); padding: 20px; }
				.header { font-size: 16px; font-weight: bold; margin-bottom: 15px; }
				.warning { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }
				.success { background: #d4edda; padding: 10px; border-radius: 4px; margin: 10px 0; }
				.info { color: #666; font-size: 13px; }
			</style>
		</head>
		<body>
			<div class="header">✅ Plan Validation Results</div>
			<div class="info">
				<p>Steps: ${validation.total_steps}</p>
				<p>Warnings: ${validation.warnings_count}</p>
				<p>Can proceed: ${validation.can_proceed ? '✅ Yes' : '⚠️ No'}</p>
			</div>
			${validation.warnings.length > 0 ? `
				<div class="warning">
					<strong>⚠️ Warnings:</strong>
					<pre>${JSON.stringify(validation.warnings, null, 2)}</pre>
				</div>
			` : '<div class="success">No issues found!</div>'}
		</body>
		</html>
	`;
}

function getPlansWebviewContent(plans: any): string {
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<style>
				body { font-family: var(--vscode-font-family); padding: 20px; }
				table { width: 100%; border-collapse: collapse; }
				th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
				th { background: #f5f5f5; font-weight: bold; }
			</style>
		</head>
		<body>
			<h2>📋 Plans</h2>
			<table>
				<tr><th>ID</th><th>Domain</th><th>Steps</th><th>Status</th></tr>
				${Array.isArray(plans) ? plans.map(p => `
					<tr><td>${p.id || 'N/A'}</td><td>${p.domain || 'N/A'}</td><td>${p.step_count || 0}</td><td>${p.status || 'pending'}</td></tr>
				`).join('') : '<tr><td colspan="4">No plans found</td></tr>'}
			</table>
		</body>
		</html>
	`;
}

function getSkillsWebviewContent(skills: any): string {
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<style>
				body { font-family: var(--vscode-font-family); padding: 20px; }
				.skill { margin: 15px 0; padding: 10px; border-left: 4px solid #0078d4; background: #f5f5f5; }
				.skill-name { font-weight: bold; }
				.skill-meta { font-size: 12px; color: #666; }
			</style>
		</head>
		<body>
			<h2>⭐ Skills</h2>
			${Array.isArray(skills) ? skills.map(s => `
				<div class="skill">
					<div class="skill-name">${s.id || 'Unknown'}</div>
					<div class="skill-meta">Domain: ${s.domain} | Quality: ${s.quality_score || 'N/A'} | Success: ${s.success_rate || 'N/A'}</div>
				</div>
			`).join('') : '<p>No skills generated yet</p>'}
		</body>
		</html>
	`;
}

function getCalibrationWebviewContent(calibration: any): string {
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<style>
				body { font-family: var(--vscode-font-family); padding: 20px; }
				.stat { margin: 10px 0; }
				.stat-label { font-weight: bold; }
				.stat-value { margin-left: 10px; font-family: monospace; }
				.warning { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }
			</style>
		</head>
		<body>
			<h2>📊 Team Calibration</h2>
			<div class="stat">
				<div class="stat-label">Success Rate:</div>
				<div class="stat-value">${calibration.success_rate || 'N/A'}</div>
			</div>
			<div class="stat">
				<div class="stat-label">Confidence Gap:</div>
				<div class="stat-value">${calibration.confidence_gap || 'N/A'}</div>
			</div>
			<div class="stat">
				<div class="stat-label">Sample Size:</div>
				<div class="stat-value">${calibration.sample_size || 'N/A'}</div>
			</div>
			${calibration.note ? `<div class="warning">${calibration.note}</div>` : ''}
		</body>
		</html>
	`;
}

export function deactivate() {
	console.log('Membria extension deactivated');
}
