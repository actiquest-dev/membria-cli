import * as vscode from 'vscode';
import { MembriaClient } from '../membriaMCPClient';

export class ChatProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'membria.chat';
    private _view?: vscode.WebviewView;

    constructor(
        private readonly _client: MembriaClient,
        private readonly _extensionUri: vscode.Uri,
    ) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage':
                    const chatResponse = await this._handleChat(data.text, data.role, data.mode);
                    webviewView.webview.postMessage({ type: 'addResponse', text: chatResponse });
                    break;
                case 'redTeamAudit':
                    const auditResponse = await this._handleAudit(data.text);
                    webviewView.webview.postMessage({ type: 'addResponse', text: auditResponse });
                    break;
                case 'loadExperts':
                    const experts = await this._loadExperts();
                    webviewView.webview.postMessage({ type: 'setExperts', experts });
                    break;
            }
        });
    }

    private async _handleChat(text: string, role: string, mode: string): Promise<string> {
        try {
            if (mode === 'basic') {
                const result = await this._client.consultExpert(text, role);
                return result.response || 'No response from expert.';
            } else {
                const result = await this._client.runOrchestration(text, mode);
                return result.response || 'Orchestration failed.';
            }
        } catch (error) {
            return `Error: ${error}`;
        }
    }

    private async _handleAudit(text: string): Promise<string> {
        try {
            const result = await this._client.redTeamAudit(text);
            return result.audit_report || 'Audit failed.';
        } catch (error) {
            return `Error: ${error}`;
        }
    }

    private async _loadExperts(): Promise<string[]> {
        try {
            const experts = await this._client.listExperts();
            return experts && experts.length > 0 ? experts : ['architect', 'implementer', 'reviewer', 'security_auditor'];
        } catch (error) {
            return ['architect'];
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    :root {
                        --panel-bg: var(--vscode-sideBar-background);
                        --item-bg: var(--vscode-editor-background);
                        --border: var(--vscode-widget-border);
                        --accent: var(--vscode-button-background);
                        --text: var(--vscode-foreground);
                        --dim: var(--vscode-descriptionForeground);
                    }
                    body { font-family: var(--vscode-font-family); color: var(--text); background-color: var(--panel-bg); padding: 0; display: flex; flex-direction: column; height: 100vh; margin: 0; overflow: hidden; }
                    
                    .header { padding: 12px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; background: rgba(255,255,255,0.03); backdrop-filter: blur(4px); }
                    .mode-row { display: flex; gap: 8px; align-items: center; }
                    .mode-row select { background: var(--vscode-dropdown-background); color: var(--vscode-dropdown-foreground); border: 1px solid var(--border); padding: 4px; border-radius: 4px; font-size: 11px; flex: 1; }
                    
                    #chat-container { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 12px; scroll-behavior: smooth; }
                    .message { padding: 10px 14px; border-radius: 8px; max-width: 85%; font-size: 13px; line-height: 1.5; position: relative; animation: fadeIn 0.2s ease-out; }
                    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
                    
                    .user-message { align-self: flex-end; background-color: var(--accent); color: var(--vscode-button-foreground); border-bottom-right-radius: 2px; }
                    .ai-message { align-self: flex-start; background-color: var(--item-bg); border: 1px solid var(--border); border-bottom-left-radius: 2px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                    
                    .input-area { padding: 12px; border-top: 1px solid var(--border); background-color: var(--panel-bg); }
                    #chat-input { width: 100%; box-sizing: border-box; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--border); padding: 10px; border-radius: 6px; resize: none; margin-bottom: 10px; font-family: inherit; font-size: 13px; }
                    #chat-input:focus { outline: 1px solid var(--accent); border-color: transparent; }
                    
                    .controls { display: flex; flex-direction: column; gap: 8px; }
                    .row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
                    
                    button { background: var(--accent); color: var(--vscode-button-foreground); border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 500; transition: filter 0.2s; }
                    button:hover { filter: brightness(1.1); }
                    .secondary-btn { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
                    
                    pre { background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; overflow-x: auto; font-family: var(--vscode-editor-font-family); font-size: 12px; margin: 8px 0; }
                    code { font-family: var(--vscode-editor-font-family); color: #ce9178; }
                    .role-tag { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; color: var(--dim); display: block; }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="mode-row">
                        <span style="font-size: 11px; opacity: 0.8">Mode:</span>
                        <select id="orchestration-mode">
                            <option value="basic">Basic Expert (Fast)</option>
                            <option value="pipeline">Pipeline (Planned)</option>
                            <option value="debate">Debate (Adversarial)</option>
                            <option value="consensus">Consensus (Balanced)</option>
                        </select>
                    </div>
                    <div class="mode-row" id="expert-row">
                        <span style="font-size: 11px; opacity: 0.8">Expert:</span>
                        <select id="role-select">
                            <option value="architect">Lead Architect</option>
                        </select>
                    </div>
                </div>

                <div id="chat-container">
                    <div class="message ai-message">
                        <span class="role-tag">Membria Council</span>
                        Welcome. I am the Orchestrator. Select a mode above and describe your technical challenge.
                    </div>
                </div>

                <div class="input-area">
                    <textarea id="chat-input" rows="3" placeholder="Explain this pattern..."></textarea>
                    <div class="controls">
                        <div class="row">
                            <button id="audit-btn" class="secondary-btn" style="flex:1">🛡️ Red Team Audit</button>
                            <button id="send-btn" style="flex:2">Engage Council</button>
                        </div>
                    </div>
                </div>

                <script>
                    const vscode = acquireVsCodeApi();
                    const chatContainer = document.getElementById('chat-container');
                    const chatInput = document.getElementById('chat-input');
                    const sendBtn = document.getElementById('send-btn');
                    const auditBtn = document.getElementById('audit-btn');
                    const roleSelect = document.getElementById('role-select');
                    const orchMode = document.getElementById('orchestration-mode');
                    const expertRow = document.getElementById('expert-row');

                    orchMode.addEventListener('change', () => {
                        expertRow.style.display = orchMode.value === 'basic' ? 'flex' : 'none';
                    });

                    function addMessage(text, isUser = false, role = '') {
                        const div = document.createElement('div');
                        div.className = 'message ' + (isUser ? 'user-message' : 'ai-message');
                        
                        let content = '';
                        if (!isUser) {
                            content += \`<span class="role-tag">\${role || 'Council'}</span>\`;
                        }
                        // Simple MD-like formatting for code blocks
                        content += text.replace(/\`\`\`([\\s\\S]*?)\`\`\`/g, '<pre><code>$1</code></pre>')
                                       .replace(/\`(.*?)\`/g, '<code>$1</code>');
                        
                        div.innerHTML = content;
                        chatContainer.appendChild(div);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }

                    sendBtn.addEventListener('click', () => {
                        const text = chatInput.value.trim();
                        if (!text) return;
                        
                        const role = roleSelect.value;
                        const mode = orchMode.value;
                        addMessage(text, true);
                        chatInput.value = '';
                        
                        vscode.postMessage({ type: 'sendMessage', text, role, mode });
                    });

                    auditBtn.addEventListener('click', () => {
                        const text = chatInput.value.trim();
                        if (!text) return;
                        
                        addMessage("Requesting Red Team Audit: " + text, true);
                        chatInput.value = '';
                        
                        vscode.postMessage({ type: 'redTeamAudit', text });
                    });

                    chatInput.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendBtn.click();
                        }
                    });

                    window.addEventListener('message', event => {
                        const message = event.data;
                        switch (message.type) {
                            case 'addResponse':
                                addMessage(message.text, false, orchMode.value === 'basic' ? roleSelect.value : 'Council Synthesis');
                                break;
                            case 'setExperts':
                                roleSelect.innerHTML = message.experts.map(e => \`<option value="\${e}">\${e.charAt(0).toUpperCase() + e.slice(1)}</option>\`).join('');
                                break;
                        }
                    });

                    // Request experts on load
                    vscode.postMessage({ type: 'loadExperts' });
                </script>
            </body>
            </html>
        `;
    }
}
