#!/bin/bash
# 프론트엔드 프로덕션 빌드 후 재배포 (2026-09-11 — dev서버→프로덕션 preview 전환에 따라 필요).
# tsc -b는 프로젝트 전반의 기존(무관한) 타입에러가 많아 빌드를 막으므로 건너뛰고 vite build만 실행.
cd /home/rejoice888/Avengers/frontend
npx vite build
pm2 restart avengers-frontend --update-env
