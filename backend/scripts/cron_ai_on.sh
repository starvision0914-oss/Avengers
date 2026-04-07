#!/bin/bash
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_ai_control on --source schedule >> /tmp/cron_ai.log 2>&1
