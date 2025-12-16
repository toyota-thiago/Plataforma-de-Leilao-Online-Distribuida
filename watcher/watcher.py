import redis
import json
import time
from datetime import datetime

REDIS_HOST = "redis-service"
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
pub = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def parse_datetime(value):
    if len(value) == 16:  # YYYY-MM-DD HH:MM
        value += ":00"
    return datetime.strptime(value, DATE_FORMAT)


def now():
    return datetime.now()

print("Auction Watcher iniciado")

while True:
    try:
        auction_ids = r.smembers("auctions")

        for auction_id in auction_ids:
            raw = r.get(f"auction:{auction_id}")
            if not raw:
                continue

            auction = json.loads(raw)

            # já encerrado apenas ignora
            if not auction.get("active", True):
                continue

            end_time = parse_datetime(auction["end_time"])

            if end_time > now():
                continue
            
            # Encerra o leilao
            auction["active"] = False
            r.set(f"auction:{auction_id}", json.dumps(auction))

            # Busca maior lance
            top = r.zrevrange(
                f"bids:{auction_id}",
                0,
                0
            )

            if not top:
                print(f"Leilão sem lances: {auction['title']}")
                continue

            bid = json.loads(top[0])

            pub.publish(
                "auction:ended",
                json.dumps({
                    "auction_id": auction_id,
                    "produto": auction["title"],
                    "preco": bid["amount"],
                    "vencedor": bid["bidder"],
                    "email": bid["email"]
                })
            )

        time.sleep(2)

    except Exception as e:
        print("Erro no watcher:", e)
        time.sleep(5)
