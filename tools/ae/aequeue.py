"""The core's queue of After Effects build requests (specs/032 T012, data-model.md, contracts/bridge-api.md).

Since specs/038 the queue itself lives in enginequeue.py (one queue per engine); this module keeps the AE functions
other parts of the studio call. $STUDIO_DATA/ae/requests/<id>/ holds request.json, bundle.tar, out/<name>.mp4|tar."""
import time

from ae import enginequeue
from ae.enginequeue import ACTIVE, FINAL, HEARTBEAT_S, HELLO_S, KEEP_S, QueueError, iso, public  # noqa: F401

now = time.time                    # tests replace it

_Q = enginequeue.Queue("ae", clock=lambda: now())
MAX_RESULT = _Q.MAX_RESULT
ID = _Q.ID
NAME = enginequeue.ENGINES["ae"]["names"]


def root():
    return _Q.root()


def lock():
    return _Q.lock()


def create(owner: str, job: str, film: str, shots: list, bundle: bytes, kind: str = "build") -> dict:
    return _Q.create(owner, job, film, shots, bundle, kind)


get = _Q.get
position = _Q.position
next_request = _Q.next_request
progress = _Q.progress
bundle_path = _Q.bundle_path
result_part = _Q.result_part
commit_result = _Q.commit_result
put_result = _Q.put_result
finish = _Q.finish
result_path = _Q.result_path
hello = _Q.hello
bridge_status = _Q.bridge_status
