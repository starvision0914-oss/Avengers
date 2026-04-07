#!/bin/bash
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_cpc2 on --source schedule >> /tmp/cron_cpc2.log 2>&1
