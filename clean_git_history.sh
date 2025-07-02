#!/bin/bash

echo "⚠️  WARNING: This will rewrite git history!"
echo "Make sure you have a backup of your repository."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "🧹 Cleaning git history..."
    
    # Remove .env.yaml and other sensitive files from all commits
    git filter-branch --force --index-filter \
        'git rm --cached --ignore-unmatch .env.yaml .env.production.yaml .env *.json graphiti-sa-key.json' \
        --prune-empty --tag-name-filter cat -- --all
    
    echo "🗑️  Cleaning up..."
    rm -rf .git/refs/original/
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
    
    echo "✅ Git history cleaned!"
    echo ""
    echo "⚠️  IMPORTANT: You need to force push to update the remote repository:"
    echo "git push origin --force --all"
    echo "git push origin --force --tags"
    echo ""
    echo "⚠️  WARNING: This will overwrite the remote history. Make sure no one else is working on the repo!"
fi