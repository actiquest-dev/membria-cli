#!/bin/bash
cd /home/membria_ai/membria-cli
git fetch origin
git reset --hard origin/master
cd backend
npm install
pm2 start ecosystem.config.js --update-env || pm2 start ecosystem.config.js
pm2 save
pm2 startup
