import * as vscode from 'vscode';
import { spawn } from 'child_process';

interface MCPRequest {
	jsonrpc: string;
	id: string | number;
	method: string;
	params?: any;
}

interface MCPResponse {
	jsonrpc: string;
	id: string | number;
	result?: any;
	error?: { code: number; message: string };
}

interface MCPTool {
	name: string;
	description?: string;
	inputSchema?: any;
}

export class MembriaClient {
	private serverPath: string;
	private process: any;
	private requestId: number = 0;
	private pendingRequests: Map<number, { resolve: (value: any) => void; reject: (error: any) => void }> = new Map();

	constructor() {
		const config = vscode.workspace.getConfiguration('membria');
		const serverPath = config.get<string>('serverPath') || '/Users/miguelaprossine/membria-cli/start_mcp_server.py';

		this.serverPath = serverPath;
		this.connect();
	}

	private connect() {
		this.process = spawn('python3', [this.serverPath], {
			env: {
				...process.env,
				PYTHONPATH: '/Users/miguelaprossine/membria-cli/src',
				VIRTUAL_ENV: '/Users/miguelaprossine/membria-cli/.venv'
			}
		});

		this.process.stdout.on('data', (data: Buffer) => {
			const lines = data.toString().split('\n').filter(line => line.trim());
			for (const line of lines) {
				if (!line) continue;
				try {
					const response: MCPResponse = JSON.parse(line);
					const pending = this.pendingRequests.get(response.id as number);
					if (pending) {
						this.pendingRequests.delete(response.id as number);
						if (response.error) {
							pending.reject(new Error(response.error.message));
						} else {
							pending.resolve(response.result);
						}
					}
				} catch (e) {
					console.error('Failed to parse MCP response:', line);
				}
			}
		});

		this.process.stderr.on('data', (data: Buffer) => {
			console.error('MCP Server stderr:', data.toString());
		});

		this.process.on('error', (error: any) => {
			console.error('MCP Server error:', error);
		});

		this.process.on('exit', (code: number) => {
			console.error('MCP Server exited with code:', code);
		});
	}

	private async sendRequest(method: string, params?: any): Promise<any> {
		const id = ++this.requestId;

		return new Promise((resolve, reject) => {
			this.pendingRequests.set(id, { resolve, reject });

			const request: MCPRequest = {
				jsonrpc: '2.0',
				id,
				method,
				params
			};

			this.process.stdin.write(JSON.stringify(request) + '\n');
		});
	}

	private async callTool(toolName: string, args: any): Promise<any> {
		return this.sendRequest('tools/call', {
			name: toolName,
			arguments: args
		});
	}

	// Public API - matches existing MembriaClient interface

	async captureDecision(statement: string, alternatives: string[], confidence: number): Promise<any> {
		return this.callTool('membria.capture_decision', {
			statement,
			alternatives,
			confidence,
			context: { module: 'vscode' }
		});
	}

	async recordOutcome(decisionId: string, status: string, score: number = 0.5): Promise<any> {
		return this.callTool('membria.record_outcome', {
			decision_id: decisionId,
			final_status: status,
			final_score: score,
			decision_domain: 'general'
		});
	}

	async getContext(statement: string, module: string = 'general', confidence: number = 0.5): Promise<any> {
		return this.callTool('membria.get_decision_context', {
			statement,
			module,
			confidence
		});
	}

	async getCalibration(domain: string = 'general'): Promise<any> {
		return this.callTool('membria.get_calibration', {
			domain
		});
	}

	async getPlanContext(domain: string, scope?: string): Promise<any> {
		return this.callTool('membria.get_plan_context', {
			domain,
			scope
		});
	}

	async validatePlan(steps: string[], domain?: string): Promise<any> {
		return this.callTool('membria.validate_plan', {
			steps,
			domain
		});
	}

	async recordPlan(
		planSteps: string[],
		domain: string,
		planConfidence: number = 0.5,
		durationEstimate?: string,
		warningsShown: number = 0,
		warningsHeeded: number = 0
	): Promise<any> {
		return this.callTool('membria.record_plan', {
			plan_steps: planSteps,
			domain,
			plan_confidence: planConfidence,
			duration_estimate: durationEstimate,
			warnings_shown: warningsShown,
			warnings_heeded: warningsHeeded
		});
	}

	async listPlans(): Promise<any[]> {
		try {
			const result = await this.sendRequest('tools/list', {});
			return result.tools || [];
		} catch (error) {
			return [];
		}
	}

	async listSkills(): Promise<any[]> {
		try {
			const result = await this.sendRequest('tools/list', {});
			return result.tools || [];
		} catch (error) {
			return [];
		}
	}

	async generateSkill(domain: string): Promise<any> {
		return this.callTool('membria.generate_skill', { domain });
	}

	async consultExpert(task: string, role: string): Promise<any> {
		return this.callTool('membria.consult_expert', { task, role });
	}

	async redTeamAudit(task: string, context?: string): Promise<any> {
		return this.callTool('membria.red_team_audit', { task, context });
	}

	async listExperts(): Promise<any[]> {
		try {
			const result = await this.callTool('membria.list_experts', {});
			return result.experts || [];
		} catch (error) {
			return ['architect'];
		}
	}

	async runOrchestration(task: string, mode: string = 'pipeline', redTeam: boolean = false): Promise<any> {
		return this.callTool('membria.run_orchestration', { task, mode, red_team: redTeam });
	}

	isAvailable(): boolean {
		return this.process && !this.process.killed;
	}

	dispose() {
		if (this.process && !this.process.killed) {
			this.process.kill();
		}
	}
}
