#!/bin/bash
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_11st_cost >> /tmp/cron_11st_cost.log 2>&1
