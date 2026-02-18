# Publishing to VS Code Marketplace

Follow these steps to make Membria visible in the VS Code Extension search.

## 1. Create a Publisher

1. Go to the [Visual Studio Marketplace Management Portal](https://marketplace.visualstudio.com/manage).
2. Log in with your Microsoft account.
3. Create a new **Publisher**.
   - **Publisher ID**: This must match the `"publisher": "membria"` in your `package.json`. If you choose a different ID, update `package.json` accordingly.

## 2. Get a Personal Access Token (PAT)

1. VS Code uses Azure DevOps for authentication. Go to [Azure DevOps](https://dev.azure.com/).
2. Click on **User settings** (circle icon in top right) -> **Personal access tokens**.
3. Create a **New Token**.
   - **Name**: `vsce-publisher`
   - **Organization**: `All accessible organizations`
   - **Scopes**: `Marketplace` (select `Manage` and `Publish`).
4. **Copy the token** immediately (it won't be shown again).

## 3. Install & Login with `vsce`

You already have `vsce` listed in `devDependencies`. You can use it via `npx`:

```bash
cd vscode-extension
npx vsce login [your-publisher-id]
# Paste your PAT when prompted
```

## 4. Package & Publish

Run the following commands to send your extension to the store:

```bash
# Verify the build first
npm run compile

# Package it into a .vsix file (for manual testing or upload)
npm run vsce-package

# Publish directly to the Marketplace
npm run publish
```

## 5. Metadata Checklist

Before publishing, ensure these fields in `package.json` are accurate:

- `displayName`: How it appears in search results.
- `description`: A clear, one-sentence pitch.
- `icon`: Ensure `media/icon.png` (128x128px) exists and looks good.
- `README.md`: This is your store page. Ensure it has screenshots.

## 6. Verification

Once published, it usually takes **5-10 minutes** for the marketplace to verify the extension. After that, it will be searchable in VS Code!
