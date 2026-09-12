#!/usr/bin/env bash
# 컴퓨터를 껐다 켰을 때, 또는 WSL을 재시작했을 때 다시 실행하는 스크립트.
# (설치 스크립트는 딱 1번만 실행하면 되고, 이후엔 이 스크립트만 쓰면 됨)
sudo service mysql start
sudo service redis-server start
pm2 resurrect 2>/dev/null || pm2 start ~/Avengers/windows_install/ecosystem.windows.config.cjs
