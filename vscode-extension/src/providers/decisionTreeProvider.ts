import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class DecisionTreeProvider implements vscode.TreeDataProvider<DecisionItem> {
	private _onDidChangeTreeData: vscode.EventEmitter<DecisionItem | undefined | null | void> = new vscode.EventEmitter<DecisionItem | undefined | null | void>();
	readonly onDidChangeTreeData: vscode.Event<DecisionItem | undefined | null | void> = this._onDidChangeTreeData.event;

	constructor(private client: MembriaClient) {}

	refresh(): void {
		this._onDidChangeTreeData.fire();
	}

	getTreeItem(element: DecisionItem): vscode.TreeItem {
		return element;
	}

	async getChildren(element?: DecisionItem): Promise<DecisionItem[]> {
		if (!element) {
			// Root level - show categories
			return [
				new DecisionItem('Recent Decisions', vscode.TreeItemCollapsibleState.Collapsed, 'recent'),
				new DecisionItem('Success Patterns', vscode.TreeItemCollapsibleState.Collapsed, 'success'),
				new DecisionItem('Failed Approaches', vscode.TreeItemCollapsibleState.Collapsed, 'failed'),
				new DecisionItem('In Progress', vscode.TreeItemCollapsibleState.Collapsed, 'pending')
			];
		}

		// Return mock data for each category
		switch (element.category) {
			case 'recent':
				return [
					new DecisionItem('Use PostgreSQL (dec_001)', vscode.TreeItemCollapsibleState.None, 'decision', {
						command: 'membria.showDecision',
						title: 'Show Decision',
						arguments: ['dec_001']
					}),
					new DecisionItem('Use Prisma ORM (dec_002)', vscode.TreeItemCollapsibleState.None, 'decision', {
						command: 'membria.showDecision',
						title: 'Show Decision',
						arguments: ['dec_002']
					})
				];
			case 'success':
				return [
					new DecisionItem('Auth0 Integration', vscode.TreeItemCollapsibleState.None, 'success'),
					new DecisionItem('JWT + Redis Sessions', vscode.TreeItemCollapsibleState.None, 'success')
				];
			case 'failed':
				return [
					new DecisionItem('Custom JWT Implementation', vscode.TreeItemCollapsibleState.None, 'failure'),
					new DecisionItem('Manual Caching Layer', vscode.TreeItemCollapsibleState.None, 'failure')
				];
			case 'pending':
				return [
					new DecisionItem('Rate Limiting Strategy (pending)', vscode.TreeItemCollapsibleState.None, 'pending')
				];
			default:
				return [];
		}
	}
}

export class DecisionItem extends vscode.TreeItem {
	constructor(
		public readonly label: string,
		public readonly collapsibleState: vscode.TreeItemCollapsibleState,
		public readonly category?: string,
		public readonly command?: vscode.Command
	) {
		super(label, collapsibleState);

		// Set icon based on category
		if (category === 'success') {
			this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
		} else if (category === 'failure') {
			this.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('charts.red'));
		} else if (category === 'pending') {
			this.iconPath = new vscode.ThemeIcon('clock', new vscode.ThemeColor('charts.yellow'));
		} else if (category === 'decision') {
			this.iconPath = new vscode.ThemeIcon('record');
		}

		this.command = command;
	}
}
