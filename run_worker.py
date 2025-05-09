from rq import Worker, Queue, Connection
import redis
import os
from dotenv import load_dotenv

load_dotenv()

listen = ['default']
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
