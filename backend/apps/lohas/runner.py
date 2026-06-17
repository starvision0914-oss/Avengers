"""In-memory job runner for Lohas selenium scripts.

Each job spawns a subprocess executing one of the scripts in `scripts/`.
Stdout is captured line-by-line on a background thread and stored in memory.
Jobs can be queried for their status and logs, and killed while running.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent / 'scripts'
MAX_LOG_LINES = 2000


@dataclass
class Job:
    id: str
    job_type: str
    status: str = 'pending'  # pending | running | success | failed | stopped
    logs: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    returncode: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                'id': self.id,
                'job_type': self.job_type,
                'status': self.status,
                'started_at': self.started_at,
                'finished_at': self.finished_at,
                'returncode': self.returncode,
                'log_count': len(self.logs),
            }

    def append(self, line: str) -> None:
        with self._lock:
            self.logs.append(line)
            if len(self.logs) > MAX_LOG_LINES:
                # keep the tail
                self.logs = self.logs[-MAX_LOG_LINES:]

    def snapshot_logs(self, since: int = 0) -> List[str]:
        with self._lock:
            return self.logs[since:]


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()


def _reap(job: Job) -> None:
    assert job.process is not None
    try:
        for raw in iter(job.process.stdout.readline, ''):  # type: ignore[union-attr]
            if not raw:
                break
            job.append(raw.rstrip('\n'))
    finally:
        job.process.wait()
        job.returncode = job.process.returncode
        with job._lock:
            if job.status == 'running':
                job.status = 'success' if job.returncode == 0 else 'failed'
            job.finished_at = time.time()
        job.append(f'[job ended, rc={job.returncode}, status={job.status}]')


def start_job(job_type: str, script_name: str, args: List[str]) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], job_type=job_type)
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        job.status = 'failed'
        job.append(f'[script not found: {script_path}]')
        job.finished_at = time.time()
        with _jobs_lock:
            _jobs[job.id] = job
        return job

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'

    try:
        proc = subprocess.Popen(
            [sys.executable, '-u', str(script_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            env=env,
            start_new_session=True,
        )
    except Exception as exc:  # pragma: no cover
        job.status = 'failed'
        job.append(f'[subprocess launch failed: {exc}]')
        job.finished_at = time.time()
        with _jobs_lock:
            _jobs[job.id] = job
        return job

    job.process = proc
    job.status = 'running'
    job.append(f'[job started, pid={proc.pid}, script={script_name}]')
    with _jobs_lock:
        _jobs[job.id] = job

    threading.Thread(target=_reap, args=(job,), daemon=True).start()
    return job


def get_job(job_id: str) -> Optional[Job]:
    with _jobs_lock:
        return _jobs.get(job_id)


def list_jobs() -> List[Job]:
    with _jobs_lock:
        return sorted(_jobs.values(), key=lambda j: j.started_at, reverse=True)


def stop_job(job_id: str) -> bool:
    job = get_job(job_id)
    if not job or job.process is None:
        return False
    if job.status != 'running':
        return False
    try:
        os.killpg(os.getpgid(job.process.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    with job._lock:
        job.status = 'stopped'
    return True
