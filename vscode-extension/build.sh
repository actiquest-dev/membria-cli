#!/bin/bash

echo "🔨 Building Membria VSCode Extension..."

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Compile TypeScript
echo "📝 Compiling TypeScript..."
npx tsc -p ./

# Verify build
if [ -d "out" ]; then
    echo "✅ Build successful!"
    echo "📂 Output directory: ./out"
    echo ""
    echo "To test the extension:"
    echo "  1. Press F5 in VSCode to launch debug session"
    echo "  2. Or package with: npm run vsce-package"
else
    echo "❌ Build failed!"
    exit 1
fi
