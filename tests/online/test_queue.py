"""Queue: FR-008a, SC-009 (specs/007 tasks T014). 20 jobs of 5 customers, N = 2."""
import threading
import time
import unittest

from helpers import Studio, film_job


class Queue(unittest.TestCase):
    def test_never_more_than_n_or_two_per_customer(self):
        from studio import db, quotas
        s = Studio(concurrency=2, interval=0.05)
        try:
            quotas.update_settings({"quota_films_default": 10})
            clients = [s.signup_verified(f"c{i}@example.com") for i in range(5)]
            ids = []
            for round_ in range(3):                      # at most 3 open jobs per customer
                for c in clients:
                    r = film_job(c, idea=f"A fox, round {round_} [slow 0.2]")
                    self.assertEqual(r.status_code, 201, r.text)
                    ids.append(r.json()["id"])
            # queue places follow the order the jobs came in
            pos = [clients[i % 5].get(f"/api/v1/jobs/{j}").json()["queue_position"] for i, j in enumerate(ids)]
            self.assertEqual(pos, list(range(1, len(ids) + 1)))
            worst, per_owner, stop = [0], [0], threading.Event()

            def watch():
                while not stop.is_set():
                    with db.read() as con:
                        rows = con.execute("SELECT owner FROM docs WHERE kind = 'job' AND status = 'running'").fetchall()
                    owners = [r[0] for r in rows]
                    worst[0] = max(worst[0], len(owners))
                    per_owner[0] = max([per_owner[0]] + [owners.count(o) for o in owners])
                    time.sleep(0.05)
            w = threading.Thread(target=watch)
            w.start()
            s.start()
            for j in ids[:5]:
                s.wait(j, timeout=120)
            # 5 more come in while the queue runs (20 in all)
            for c in clients:
                ids.append(film_job(c, idea="Late fox [slow 0.1]").json()["id"])
            for j in ids:
                self.assertEqual(s.wait(j, timeout=180)["status"], "done")
            stop.set()
            w.join()
            self.assertEqual(len(ids), 20)
            self.assertLessEqual(worst[0], 2)
            self.assertGreaterEqual(worst[0], 1)
            self.assertLessEqual(per_owner[0], 1)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
