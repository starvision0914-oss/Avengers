module.exports = {
  apps: [
    {
      name: 'avengers-backend',
      cwd: '/home/rejoice888/Avengers/backend',
      script: 'manage.py',
      args: 'runserver 0.0.0.0:8001',
      interpreter: '/usr/bin/python3',
      env: {
        PYTHONPATH: '/home/rejoice888/.local/lib/python3.12/site-packages',
      },
    },
    {
      name: 'avengers-frontend',
      cwd: '/home/rejoice888/Avengers/frontend',
      script: 'node_modules/.bin/vite',
      args: '--host 0.0.0.0 --port 5173',
    },
  ],
};
