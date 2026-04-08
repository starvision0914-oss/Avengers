#!/bin/bash
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py run_ai_schedule >> /tmp/cron_ai_schedule.log 2>&1
