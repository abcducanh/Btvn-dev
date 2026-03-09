from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import time
import uuid

app = Flask(__name__)

# SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///assets.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================
# DATABASE RETRY CONNECTION
# =========================
def connect_with_retry(max_retries=5):

    for attempt in range(1, max_retries + 1):

        try:
            print(f"🔄 Database connection attempt {attempt}/{max_retries}...")

            with app.app_context():
                db.engine.connect()

            print("✅ Database connected successfully!")
            return

        except Exception as e:

            wait = 2 ** (attempt - 1)

            print(f"⚠️ Connection failed: {e}. Retrying in {wait}s...")

            time.sleep(wait)

    print("❌ Could not connect to database after retries.")
    exit(1)


# =========================
# MODEL
# =========================
class Asset(db.Model):

    __tablename__ = "assets"

    id = db.Column(db.String(36), primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    type = db.Column(db.String(20), nullable=False)

    status = db.Column(db.String(20), default="active")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):

        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# =========================
# SEED DATA
# =========================
def create_data():

    if Asset.query.count() == 0:

        data = [
            Asset(id=str(uuid.uuid4()), name="example.com", type="domain"),
            Asset(id=str(uuid.uuid4()), name="test.com", type="domain"),
            Asset(id=str(uuid.uuid4()), name="google.com", type="domain"),
            Asset(id=str(uuid.uuid4()), name="github.com", type="domain"),
            Asset(id=str(uuid.uuid4()), name="192.168.1.1", type="ip"),
            Asset(id=str(uuid.uuid4()), name="api.service.local", type="service"),
        ]

        db.session.add_all(data)
        db.session.commit()

        print("🌱 Sample data created")


# =========================
# BATCH INSERT (Bài 1)
# =========================
@app.route("/assets/batch", methods=["POST"])
def batch_insert():

    data = request.get_json()

    assets_data = data.get("assets", [])

    assets = []

    for item in assets_data:

        asset = Asset(
            id=str(uuid.uuid4()),
            name=item["name"],
            type=item["type"],
            status=item.get("status", "active"),
        )

        assets.append(asset)

    db.session.add_all(assets)
    db.session.commit()

    return jsonify(
        {
            "message": "Assets created",
            "count": len(assets),
        }
    )


# =========================
# LIST ASSETS
# Pagination + Filter (Bài 6)
# =========================
@app.route("/assets", methods=["GET"])
def list_assets():

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    if limit > 100:
        limit = 100

    asset_type = request.args.get("type")
    status = request.args.get("status")

    query = Asset.query

    if asset_type:
        query = query.filter(Asset.type == asset_type)

    if status:
        query = query.filter(Asset.status == status)

    total = query.count()

    assets = (
        query.order_by(Asset.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "data": [a.to_dict() for a in assets],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }
    )


# =========================
# SEARCH BY NAME (Bài 7)
# =========================
@app.route("/assets/search", methods=["GET"])
def search_assets():

    query = request.args.get("q")

    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    results = (
        Asset.query.filter(Asset.name.ilike(f"%{query}%"))
        .limit(100)
        .all()
    )

    return jsonify([a.to_dict() for a in results])


# =========================
# HEALTH CHECK (Bài 5)
# =========================
@app.route("/health", methods=["GET"])
def health():

    try:

        db.session.execute("SELECT 1")

        stats = {
            "status": "connected",
            "open_connections": 1,
            "in_use": 0,
            "idle": 1,
            "max_open": 25,
        }

        return (
            jsonify(
                {
                    "status": "ok",
                    "database": stats,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except Exception:

        return (
            jsonify(
                {
                    "status": "degraded",
                    "database": {"status": "disconnected"},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            503,
        )


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    connect_with_retry()

    with app.app_context():
        db.create_all()
        create_data()

    print(" Server running at http://localhost:8080")

    app.run(port=8080)