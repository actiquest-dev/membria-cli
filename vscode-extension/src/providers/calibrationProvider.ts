import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class CalibrationProvider implements vscode.TreeDataProvider<CalibrationItem> {
	private _onDidChangeTreeData: vscode.EventEmitter<CalibrationItem | undefined | null | void> = new vscode.EventEmitter<CalibrationItem | undefined | null | void>();
	readonly onDidChangeTreeData: vscode.Event<CalibrationItem | undefined | null | void> = this._onDidChangeTreeData.event;

	constructor(private client: MembriaClient) {}

	refresh(): void {
		this._onDidChangeTreeData.fire();
	}

	getTreeItem(element: CalibrationItem): vscode.TreeItem {
		return element;
	}

	async getChildren(element?: CalibrationItem): Promise<CalibrationItem[]> {
		if (!element) {
			// Root level - show domains
			const domains = ['database', 'auth', 'api', 'cache', 'messaging'];
			return domains.map(domain =>
				new CalibrationItem(domain, vscode.TreeItemCollapsibleState.Collapsed, 'domain')
			);
		}

		// Return calibration data for domain
		if (element.category === 'domain') {
			return [
				new CalibrationItem('Success Rate: 85%', vscode.TreeItemCollapsibleState.None, 'metric'),
				new CalibrationItem('Sample Size: 15', vscode.TreeItemCollapsibleState.None, 'metric'),
				new CalibrationItem('Confidence Gap: +8%', vscode.TreeItemCollapsibleState.None, 'metric'),
				new CalibrationItem('Trend: Improving', vscode.TreeItemCollapsibleState.None, 'metric')
			];
		}

		return [];
	}
}

export class CalibrationItem extends vscode.TreeItem {
	constructor(
		public readonly label: string,
		public readonly collapsibleState: vscode.TreeItemCollapsibleState,
		public readonly category?: string
	) {
		super(label, collapsibleState);

		if (category === 'metric') {
			this.iconPath = new vscode.ThemeIcon('graph');
		} else {
			this.iconPath = new vscode.ThemeIcon('folder');
		}
	}
}
