import * as vscode from 'vscode';
import axios, { AxiosInstance } from 'axios';

export class MembriaClient {
	private client: AxiosInstance;
	private baseUrl: string;

	constructor() {
		const config = vscode.workspace.getConfiguration('membria');
		const host = config.get<string>('serverHost') || 'localhost';
		const port = config.get<number>('serverPort') || 6379;

		this.baseUrl = `http://${host}:${port}`;
		this.client = axios.create({
			baseURL: this.baseUrl,
			timeout: 5000
		});
	}

	async captureDecision(statement: string, alternatives: string[], confidence: number): Promise<any> {
		try {
			const response = await this.client.post('/api/decision/capture', {
				statement,
				alternatives,
				confidence
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to capture decision: ${error}`);
		}
	}

	async recordOutcome(decisionId: string, status: string, score: number = 0.5): Promise<any> {
		try {
			const response = await this.client.post('/api/decision/outcome', {
				decision_id: decisionId,
				final_status: status,
				final_score: score
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to record outcome: ${error}`);
		}
	}

	async getContext(statement: string, module: string = 'general', confidence: number = 0.5): Promise<any> {
		try {
			const response = await this.client.get('/api/decision/context', {
				params: { statement, module, confidence }
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to get context: ${error}`);
		}
	}

	async getCalibration(domain: string = 'general'): Promise<any> {
		try {
			const response = await this.client.get('/api/calibration', {
				params: { domain }
			});
			return response.data;
		} catch (error) {
			// Return empty calibration if not available
			return {
				domain,
				success_rate: 0,
				confidence_gap: 0,
				sample_size: 0,
				note: 'No calibration data available yet'
			};
		}
	}

	async getPlanContext(domain: string, scope?: string): Promise<any> {
		try {
			const response = await this.client.get('/api/plan/context', {
				params: { domain, scope }
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to get plan context: ${error}`);
		}
	}

	async validatePlan(steps: string[], domain?: string): Promise<any> {
		try {
			const response = await this.client.post('/api/plan/validate', {
				steps,
				domain
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to validate plan: ${error}`);
		}
	}

	async recordPlan(
		planSteps: string[],
		domain: string,
		confidence: number = 0.5,
		durationEstimate?: string,
		warningsShown: number = 0,
		warningsHeeded: number = 0
	): Promise<any> {
		try {
			const response = await this.client.post('/api/plan/record', {
				plan_steps: planSteps,
				domain,
				plan_confidence: confidence,
				duration_estimate: durationEstimate,
				warnings_shown: warningsShown,
				warnings_heeded: warningsHeeded
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to record plan: ${error}`);
		}
	}

	async listPlans(): Promise<any[]> {
		try {
			// This would call the CLI command and parse output
			// For now, return empty array
			return [];
		} catch (error) {
			throw new Error(`Failed to list plans: ${error}`);
		}
	}

	async listSkills(): Promise<any[]> {
		try {
			// This would call the CLI command and parse output
			// For now, return empty array
			return [];
		} catch (error) {
			throw new Error(`Failed to list skills: ${error}`);
		}
	}

	async generateSkill(domain: string): Promise<any> {
		try {
			const response = await this.client.post('/api/skill/generate', {
				domain
			});
			return response.data;
		} catch (error) {
			throw new Error(`Failed to generate skill: ${error}`);
		}
	}

	async getSkillForDomain(domain: string): Promise<any> {
		try {
			const response = await this.client.get(`/api/skill/${domain}`);
			return response.data;
		} catch (error) {
			return null;
		}
	}

	async checkReadiness(): Promise<any> {
		try {
			const response = await this.client.get('/api/skill/readiness');
			return response.data;
		} catch (error) {
			return {};
		}
	}

	isAvailable(): boolean {
		return this.baseUrl !== '';
	}
}
