from flask import Flask, render_template, request, Response, jsonify
from datetime import datetime
import uuid
import redis
import json

app = Flask(__name__)
r = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)
pub = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def now_local():
    return datetime.now()

def parse_local_datetime(value: str) -> datetime:
    """
    Aceita:
    - YYYY-MM-DDTHH:MM
    - YYYY-MM-DDTHH:MM:SS
    Converte para datetime LOCAL
    """
    value = value.replace("T", " ")
    if len(value) == 16:
        value += ":00"
    return datetime.strptime(value, DATE_FORMAT)

def format_local_datetime(dt: datetime) -> str:
    return dt.strftime(DATE_FORMAT)


class AuctionStorage:

    @staticmethod
    def create_auction(data: dict) -> str:
        auction_id = str(uuid.uuid4())

        auction = {
            'id': auction_id,
            'title': data['title'],
            'description': data['description'],
            'initial_price': float(data['initial_price']),
            'end_time': data['end_time'].replace("T", " "),
            'active': True,
            'created_at': format_local_datetime(now_local())
        }

        r.set(f"auction:{auction_id}", json.dumps(auction))
        r.delete(f"bids:{auction_id}")
        r.sadd("auctions", auction_id)
        
        pub.publish(
        "auctions:events",
        json.dumps({
            "type": "auction_created",
            "auction_id": auction_id,
            "title": auction['title']
            })
        )
        
        return auction_id


    @staticmethod
    def get_auction(auction_id: str):
        data = r.get(f"auction:{auction_id}")
        return json.loads(data) if data else None

    @staticmethod
    def get_all_auctions():
        ids = r.smembers("auctions")
        result = []

        for auction_id in ids:
            auction = AuctionStorage.get_auction(auction_id)
            if not auction:
                continue

            top = r.zrevrange(f"bids:{auction_id}", 0, 0, withscores=True)
            highest = top[0][1] if top else auction['initial_price']
            bid_count = r.zcard(f"bids:{auction_id}")

            end_time = parse_local_datetime(auction['end_time'])

            auction['current_bid'] = highest
            auction['bid_count'] = bid_count
            auction['active'] = end_time > now_local()

            result.append(auction)

        return result



    @staticmethod
    def add_bid(auction_id: str, data: dict):
        auction = AuctionStorage.get_auction(auction_id)
        if not auction:
            return False, "not_found"

        end_time = parse_local_datetime(auction['end_time'])
        if end_time <= now_local():
            return False, "expired"

        top = r.zrevrange(f"bids:{auction_id}", 0, 0, withscores=True)
        current = top[0][1] if top else auction['initial_price']

        amount = float(data['amount'])
        if amount <= current:
            return False, current

        bid = {
            'id': str(uuid.uuid4()),
            'auction_id': auction_id,
            'bidder': data.get('bidder', 'Anonymous'),
            'amount': amount,
            'timestamp': format_local_datetime(now_local())
        }

        r.zadd(
            f"bids:{auction_id}",
            {json.dumps(bid): amount}
        )

        # Pub/Sub
        pub.publish(
            f"auction:{auction_id}:events",
            json.dumps({
                "type": "bid_placed",
                "auction_id": auction_id,
                "amount": amount,
                "bidder": bid['bidder'],
                "timestamp": bid['timestamp']
            })
        )

        return True, None

    @staticmethod
    def get_bids(auction_id: str):
        bids = r.zrevrange(f"bids:{auction_id}", 0, -1)
        return [json.loads(b) for b in bids]

# ---------------- Routes ----------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create-auction', methods=['GET', 'POST'])
def create_auction():
    if request.method == 'GET':
        return render_template('create_auction.html')
    data = request.get_json() if request.is_json else request.form
    required = ['title', 'description', 'initial_price', 'end_time']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    end_time = parse_local_datetime(data['end_time'])
    if end_time <= now_local():
        return jsonify({'error': 'End time must be in the future'}), 400

    auction_id = AuctionStorage.create_auction(data)
    return jsonify({'success': True, 'auction_id': auction_id}), 201


@app.route('/view-auctions')
def view_auctions():
    return render_template('view_auctions.html')


@app.route('/auction/<auction_id>')
def auction_details(auction_id):
    return render_template('auction_details.html', auction_id=auction_id)


# --------- API ---------

@app.route('/api/auctions')
def api_auctions():
    return jsonify({'auctions': AuctionStorage.get_all_auctions()})


@app.route('/api/auction/<auction_id>')
def api_auction_details(auction_id):
    auction = AuctionStorage.get_auction(auction_id)
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    bids = AuctionStorage.get_bids(auction_id)
    auction['active'] = parse_local_datetime(auction['end_time']) > now_local()
    return jsonify({'auction': auction, 'bids': bids})


@app.route('/place-bid', methods=['POST'])
def place_bid():
    data = request.get_json() if request.is_json else request.form
    if 'auction_id' not in data or 'amount' not in data:
        return jsonify({'error': 'Missing fields auction_id or amount'}), 400
    success, info = AuctionStorage.add_bid(data['auction_id'], data)
    if success:
        return jsonify({'success': True, 'message': 'Bid placed successfully'}), 200
    elif info == "not_found":
        return jsonify({'error': 'Auction not found'}), 404
    elif info == "expired":
        return jsonify({'error': 'Auction expired'}), 400
    else:
        return jsonify({'error': f'Bid must be higher than {info}'}), 400


# --------- SSE ---------

@app.route('/stream/auction/<auction_id>')
def stream_auction(auction_id):
    def event_stream():
        ps = pub.pubsub()
        channel = f"auction:{auction_id}:events"
        ps.subscribe(channel)

        for message in ps.listen():
            if message['type'] != 'message':
                continue
            yield f"data: {message['data']}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
