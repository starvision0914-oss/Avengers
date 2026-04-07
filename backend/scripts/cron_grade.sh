#!/bin/bash
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_grade >> /tmp/cron_grade.log 2>&1
/usr/bin/python3 manage.py crawl_11st_grade >> /tmp/cron_grade.log 2>&1
