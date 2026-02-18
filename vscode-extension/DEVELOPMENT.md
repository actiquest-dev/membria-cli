# Development Guide

## Setup

### Prerequisites
- Node.js 14+ (check with `node --version`)
- VSCode installed
- `@vscode/vsce` for packaging

### Initial Setup
```bash
cd vscode-extension
npm install
```

## Building

### Development Build
```bash
npm run compile
```

### Watch Mode (auto-recompile on save)
```bash
npm run watch
```

### Bundled Release Build
```bash
npm run vsce-package
```

## Testing

### Run Tests
```bash
npm test
```

### Manual Testing
1. Press `F5` in VSCode to launch extension in debug mode
2. A new VSCode window opens with the extension loaded
3. Test commands and sidebar views
4. Press `Ctrl+Shift+D` in debug window, then red square to stop

### Debug in VSCode
1. Set breakpoints in TypeScript code
2. Run Debug → Start Debugging (F5)
3. Extension loads with breakpoints active
4. Outputs appear in VSCode Debug Console

## Code Structure

```
vscode-extension/
├── src/
│   ├── extension.ts           # Main extension entry point
│   ├── membriaClient.ts       # HTTP client to MCP server
│   └── providers/
│       ├── decisionTreeProvider.ts      # Decision sidebar
│       ├── calibrationProvider.ts       # Calibration sidebar
│       ├── skillsProvider.ts           # Skills sidebar
│       ├── plansProvider.ts            # Plans sidebar
│       ├── hoverProvider.ts            # Hover context display
│       └── decorationProvider.ts       # Inline warnings
├── package.json               # Extension metadata
├── tsconfig.json             # TypeScript config
└── README.md                 # User documentation
```

## Architecture

### Event Flow
```
User Command (e.g., captureDecision)
    ↓
extension.ts:registerCommands()
    ↓
membriaClient.captureDecision()
    ↓
HTTP POST to MCP Server
    ↓
MCP Server (Python)
    ↓
FalkorDB + OutcomeTracker
    ↓
Response back to VSCode
    ↓
Update TreeDataProvider / Show message
```

### TreeDataProvider Pattern
Each sidebar view implements `vscode.TreeDataProvider<ItemType>`:
```typescript
interface vscode.TreeDataProvider<T> {
  getTreeItem(element: T): vscode.TreeItem;
  getChildren(element?: T): ProviderResult<T[]>;
  onDidChangeTreeData?: Event<T | undefined | null | void>;
}
```

Example flow:
1. User expands "Decisions" in sidebar
2. VSCode calls `decisionTreeProvider.getChildren(undefined)`
3. Returns categories: Recent, Success, Failed, Pending
4. User clicks "Success", VSCode calls `getChildren(element)` with that element
5. Returns list of successful decisions as child items

### Webview Panels
Commands like `membria.getContext` open webview panels:
```typescript
const panel = vscode.window.createWebviewPanel(
  'membriaContext',              // Internal ID
  'Decision Context',             // Display title
  vscode.ViewColumn.Beside,       // Where to show
  {}                              // Options
);

panel.webview.html = htmlContent; // Set content
```

## Common Tasks

### Add New Command
1. In `extension.ts`, add to `registerCommands()`:
```typescript
context.subscriptions.push(
  vscode.commands.registerCommand('membria.myCommand', async () => {
    // Your command logic
  })
);
```

2. Add to `package.json` commands array:
```json
{
  "command": "membria.myCommand",
  "title": "My Command",
  "category": "Membria"
}
```

3. Add keyboard shortcut (optional) to `package.json` keybindings:
```json
{
  "command": "membria.myCommand",
  "key": "ctrl+shift+m m",
  "when": "editorTextFocus"
}
```

### Add New Tree View
1. Create `src/providers/myProvider.ts`:
```typescript
export class MyProvider implements vscode.TreeDataProvider<MyItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<MyItem | undefined>;
  readonly onDidChangeTreeData: vscode.Event<MyItem | undefined>;

  constructor(private client: MembriaClient) {
    this._onDidChangeTreeData = new vscode.EventEmitter<MyItem | undefined>();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
  }

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: MyItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: MyItem): Promise<MyItem[]> {
    if (!element) {
      // Return root items
      return [];
    }
    // Return children of element
    return [];
  }
}

export class MyItem extends vscode.TreeItem {
  constructor(label: string) {
    super(label);
  }
}
```

2. Register in `extension.ts`:
```typescript
const myProvider = new MyProvider(client);
vscode.window.registerTreeDataProvider('membria.myView', myProvider);
```

3. Add to `package.json`:
```json
{
  "id": "membria.myView",
  "name": "My View",
  "when": "view == membria.myView"
}
```

### Add API to MembriaClient
1. Add method in `membriaClient.ts`:
```typescript
async myMethod(param: string): Promise<any> {
  try {
    const response = await this.client.get(`/api/my-endpoint`, {
      params: { param }
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to call my method: ${error}`);
  }
}
```

2. Use in commands:
```typescript
const result = await client.myMethod('value');
```

## Debugging Tips

### Check MCP Server Connection
Add console logs:
```typescript
async captureDecision(statement: string, ...): Promise<any> {
  try {
    console.log(`Calling MCP server at ${this.baseUrl}`);
    const response = await this.client.post(...);
    console.log('Response:', response.data);
    return response.data;
  } catch (error) {
    console.error('MCP error:', error);
    throw error;
  }
}
```

View in VSCode Debug Console when testing.

### Check TreeDataProvider
Add logging in getChildren:
```typescript
async getChildren(element?: PlanItem): Promise<PlanItem[]> {
  console.log('getChildren called with:', element?.label);
  // ... your logic
  console.log('Returning children:', children);
  return children;
}
```

Refresh sidebar view to see logs in Debug Console.

### Check Webview Content
Log HTML generation:
```typescript
panel.webview.html = htmlContent;
console.log('Webview HTML length:', htmlContent.length);
```

If webview is blank, check HTML validity and console errors.

## Performance Considerations

### Caching
Tree providers are called frequently. Cache expensive operations:
```typescript
private cache: Map<string, any> = new Map();

async getChildren(element?: MyItem): Promise<MyItem[]> {
  const cacheKey = element?.id || 'root';
  if (this.cache.has(cacheKey)) {
    return this.cache.get(cacheKey);
  }

  const children = await this.client.fetch(element);
  this.cache.set(cacheKey, children);
  return children;
}
```

Clear cache on refresh:
```typescript
refresh(): void {
  this.cache.clear();
  this._onDidChangeTreeData.fire(undefined);
}
```

### Debouncing
For decoration provider updates on text changes:
```typescript
private updateTimer: NodeJS.Timeout | undefined;

onDidChangeTextDocument(event): void {
  if (this.updateTimer) clearTimeout(this.updateTimer);
  this.updateTimer = setTimeout(() => {
    this.updateDecorations(editor);
  }, 500);  // Wait 500ms after user stops typing
}
```

## Publishing

### To VSCode Marketplace
1. Create publisher account at https://marketplace.visualstudio.com
2. Create personal access token
3. Login with vsce:
```bash
vsce login <publisher-name>
```

4. Update version in `package.json`
5. Package:
```bash
vsce package
```

6. Publish:
```bash
vsce publish
```

## Resources

- [VSCode Extension API](https://code.visualstudio.com/api)
- [VSCode Webview API](https://code.visualstudio.com/api/extension-guides/webview)
- [TreeDataProvider Guide](https://code.visualstudio.com/api/extension-guides/tree-view)
- [Hover Provider](https://code.visualstudio.com/api/references/vscode-api#languages.registerHoverProvider)
