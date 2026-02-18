import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class PlansProvider implements vscode.TreeDataProvider<PlanItem> {
	private _onDidChangeTreeData: vscode.EventEmitter<PlanItem | undefined | null | void> = new vscode.EventEmitter<PlanItem | undefined | null | void>();
	readonly onDidChangeTreeData: vscode.Event<PlanItem | undefined | null | void> = this._onDidChangeTreeData.event;

	constructor(private client: MembriaClient) {}

	refresh(): void {
		this._onDidChangeTreeData.fire();
	}

	getTreeItem(element: PlanItem): vscode.TreeItem {
		return element;
	}

	async getChildren(element?: PlanItem): Promise<PlanItem[]> {
		if (!element) {
			// Root level - show plans by status
			return [
				new PlanItem('Completed', vscode.TreeItemCollapsibleState.Collapsed, 'status'),
				new PlanItem('In Progress', vscode.TreeItemCollapsibleState.Collapsed, 'status'),
				new PlanItem('Pending', vscode.TreeItemCollapsibleState.Collapsed, 'status')
			];
		}

		// Return plans for status
		if (element.category === 'status') {
			if (element.label === 'Completed') {
				return [
					new PlanItem('Auth System (5 steps)', vscode.TreeItemCollapsibleState.Collapsed, 'plan'),
					new PlanItem('Database Setup (3 steps)', vscode.TreeItemCollapsibleState.Collapsed, 'plan')
				];
			} else if (element.label === 'In Progress') {
				return [
					new PlanItem('API Layer (4 steps)', vscode.TreeItemCollapsibleState.Collapsed, 'plan')
				];
			} else {
				return [
					new PlanItem('Caching Strategy (2 steps)', vscode.TreeItemCollapsibleState.Collapsed, 'plan')
				];
			}
		}

		// Return steps for plan
		if (element.category === 'plan') {
			return [
				new PlanItem('Step 1: Setup', vscode.TreeItemCollapsibleState.None, 'step'),
				new PlanItem('Step 2: Configure', vscode.TreeItemCollapsibleState.None, 'step'),
				new PlanItem('Step 3: Test', vscode.TreeItemCollapsibleState.None, 'step')
			];
		}

		return [];
	}
}

export class PlanItem extends vscode.TreeItem {
	constructor(
		public readonly label: string,
		public readonly collapsibleState: vscode.TreeItemCollapsibleState,
		public readonly category?: string
	) {
		super(label, collapsibleState);

		if (category === 'plan') {
			this.iconPath = new vscode.ThemeIcon('checklist');
		} else if (category === 'step') {
			this.iconPath = new vscode.ThemeIcon('circle-outline');
		} else {
			this.iconPath = new vscode.ThemeIcon('folder');
		}
	}
}
