#!/bin/bash
# 야구단 매니저 게임 자동 경기 (쿨다운이 끝났으면 자동 진행, 안 끝났으면 건너뜀)
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py play_scheduled_match >> /tmp/cron_game_match.log 2>&1
