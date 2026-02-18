import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class SkillsProvider implements vscode.TreeDataProvider<SkillItem> {
	private _onDidChangeTreeData: vscode.EventEmitter<SkillItem | undefined | null | void> = new vscode.EventEmitter<SkillItem | undefined | null | void>();
	readonly onDidChangeTreeData: vscode.Event<SkillItem | undefined | null | void> = this._onDidChangeTreeData.event;

	constructor(private client: MembriaClient) {}

	refresh(): void {
		this._onDidChangeTreeData.fire();
	}

	getTreeItem(element: SkillItem): vscode.TreeItem {
		return element;
	}

	async getChildren(element?: SkillItem): Promise<SkillItem[]> {
		if (!element) {
			// Root level - show skills by domain
			return [
				new SkillItem('sk-auth-v2', vscode.TreeItemCollapsibleState.Collapsed, 'skill', {
					quality: 0.82,
					domain: 'auth',
					successRate: 0.89
				}),
				new SkillItem('sk-database-v3', vscode.TreeItemCollapsibleState.Collapsed, 'skill', {
					quality: 0.85,
					domain: 'database',
					successRate: 0.92
				}),
				new SkillItem('sk-api-v1', vscode.TreeItemCollapsibleState.Collapsed, 'skill', {
					quality: 0.71,
					domain: 'api',
					successRate: 0.78
				})
			];
		}

		// Return zones for skill
		if (element.category === 'skill' && element.data?.quality) {
			return [
				new SkillItem(`Quality: ${(element.data.quality * 100).toFixed(0)}%`, vscode.TreeItemCollapsibleState.None, 'metric'),
				new SkillItem(`Success Rate: ${(element.data.successRate * 100).toFixed(0)}%`, vscode.TreeItemCollapsibleState.None, 'metric'),
				new SkillItem('Green Zone (Use Confidently)', vscode.TreeItemCollapsibleState.Collapsed, 'zone'),
				new SkillItem('Yellow Zone (Consider Carefully)', vscode.TreeItemCollapsibleState.Collapsed, 'zone'),
				new SkillItem('Red Zone (Avoid)', vscode.TreeItemCollapsibleState.Collapsed, 'zone')
			];
		}

		// Return patterns for zones
		if (element.category === 'zone') {
			const patterns = [
				'PostgreSQL for database',
				'Auth0 for authentication',
				'JWT + Redis sessions'
			];
			return patterns.map(p =>
				new SkillItem(p, vscode.TreeItemCollapsibleState.None, 'pattern')
			);
		}

		return [];
	}
}

export class SkillItem extends vscode.TreeItem {
	constructor(
		public readonly label: string,
		public readonly collapsibleState: vscode.TreeItemCollapsibleState,
		public readonly category?: string,
		public readonly data?: any
	) {
		super(label, collapsibleState);

		if (category === 'skill') {
			this.iconPath = new vscode.ThemeIcon('star');
		} else if (category === 'zone') {
			this.iconPath = new vscode.ThemeIcon('filter');
		} else if (category === 'pattern') {
			this.iconPath = new vscode.ThemeIcon('symbol-method');
		} else {
			this.iconPath = new vscode.ThemeIcon('info');
		}
	}
}
