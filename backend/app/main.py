from pathlib import Path
import os
from math import radians, sin, cos, sqrt, atan2

try:
    load_dotenv = __import__("dotenv").load_dotenv
except ImportError:
    load_dotenv = lambda *args, **kwargs: None

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import random

from app.services.risk_engine import (
    compute_risk_score,
    RiskInput,
    LocationPoint,
)
from app.services.supabase_client import (
    get_supabase_client,
    insert_location_point,
    upsert_user_profile,
    upsert_tracking_session,
)

app = FastAPI(
    title="RakshaAI Backend",
    description="Consent-Based Real-Time Safety Tracking System",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
STATIC_DIR = BASE_DIR / "static"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "rakshaai-admin-secret")

SUPABASE_CLIENT = get_supabase_client()

app.mount("/public", StaticFiles(directory=BASE_DIR / "public"), name="public")
app.mount("/admin", StaticFiles(directory=BASE_DIR / "admin"), name="admin")

def require_admin_token(admin_token: str | None):
    if admin_token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin token required")

# -----------------------------
# AI Risk Request
# -----------------------------

class RiskRequest(BaseModel):
    user_id: str = "demo_user"
    lat: float
    lng: float
    speed_kmh: float = 0.0
    previous_speed_kmh: float = 0.0
    battery_percent: int = 100
    sos_triggers_last_30min: int = 0
    stationary_minutes: int = 0
    hour: int = 14


# -----------------------------
# Real Location Request
# -----------------------------

class RealLocationRequest(BaseModel):
    user: str
    lat: float
    lng: float
    permission: str = "GRANTED"
    permission_time: str = "Not available"
    speed: float = 0
    accuracy: float = 999
    battery: int | str = "Unknown"


# -----------------------------
# In-memory database
# -----------------------------

users = {}

# Structure:
# users = {
#   "Navya": {
#       "user": "Navya",
#       "lat": 17.3,
#       "lng": 78.4,
#       "permission": "GRANTED",
#       "permission_time": "...",
#       "started_at": "...",
#       "last_seen": "...",
#       "status": "ONLINE",
#       "speed": 0,
#       "accuracy": 20,
#       "vehicle": "Walking",
#       "route": [[lat,lng], [lat,lng]]
#   }
# }


# -----------------------------
# Helper functions
# -----------------------------

def now_iso():
    return datetime.utcnow().isoformat()


def detect_vehicle(speed_kmh: float):
    if speed_kmh <= 1:
        return "Stopped"
    elif speed_kmh <= 6:
        return "Walking"
    elif speed_kmh <= 20:
        return "Bike / Auto"
    elif speed_kmh <= 80:
        return "Car / Bus"
    else:
        return "Train / Highway Vehicle"


def is_user_online(last_seen: str):
    if not last_seen:
        return False

    last = datetime.fromisoformat(last_seen)
    diff = (datetime.utcnow() - last).total_seconds()

    return diff <= 20


def calculate_real_risk(user):
    score = 0
    reasons = []
    battery = user.get("battery", 100)
    speed = user.get("speed", 0)
    last_seen = user.get("last_seen")
    route = user.get("route", [])
    current_hour = datetime.now().hour

    # Low battery
    if isinstance(battery, (int, float)) and battery <= 15:
        score += 30
        reasons.append("Low battery")

    # Night time
    if current_hour >= 22 or current_hour <= 5:
        score += 25
        reasons.append("Night time movement")

    # No movement: last 3 route points almost same
    if len(route) >= 3:
        p1 = route[-1]
        p2 = route[-2]
        p3 = route[-3]
        if p1 == p2 == p3 or speed <= 1:
            score += 30
            reasons.append("No movement detected")

    # Offline / page closed
    if last_seen and not is_user_online(last_seen):
        score += 40
        reasons.append("Location sharing stopped / offline")

    if score >= 80:
        band = "DANGER"
        alert = True
    elif score >= 50:
        band = "ALERT"
        alert = True
    elif score >= 25:
        band = "WATCH"
        alert = False
    else:
        band = "SAFE"
        alert = False

    return {
        "risk_score": min(score, 100),
        "risk_band": band,
        "reasons": reasons,
        "auto_alert": alert
    }


def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def calculate_total_distance(route):
    total = 0
    for i in range(1, len(route)):
        total += distance_km(
            route[i-1][0], route[i-1][1],
            route[i][0], route[i][1]
        )
    return round(total, 2)


# -----------------------------
# Basic APIs
# -----------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(BASE_DIR / "admin" / "dashboard.html")


@app.get("/share")
def share_location_page():
    return FileResponse(BASE_DIR / "public" / "phone_sender.html")


@app.get("/phone_sender.html")
def phone_sender_page():
    return FileResponse(BASE_DIR / "public" / "phone_sender.html")


@app.get("/phone_sender")
def phone_sender_alias():
    return FileResponse(BASE_DIR / "public" / "phone_sender.html")


@app.get("/sender")
def phone_sender_simple():
    return FileResponse(BASE_DIR / "public" / "phone_sender.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "RakshaAI"
    }


@app.get("/api")
def api_root():
    return {
        "message": "RakshaAI API Running",
        "status": "success"
    }


# -----------------------------
# AI Risk API
# -----------------------------

@app.post("/risk/check")
def check_risk(data: RiskRequest):

    current_location = LocationPoint(
        lat=data.lat,
        lng=data.lng,
        timestamp=datetime(2024, 6, 15, data.hour, 0, 0),
        speed_kmh=data.speed_kmh,
    )

    previous_location = LocationPoint(
        lat=data.lat,
        lng=data.lng,
        timestamp=datetime(2024, 6, 15, data.hour, 0, 0),
        speed_kmh=data.previous_speed_kmh,
    )

    risk_input = RiskInput(
        user_id=data.user_id,
        current_location=current_location,
        previous_location=previous_location,
        battery_percent=data.battery_percent,
        sos_triggers_last_30min=data.sos_triggers_last_30min,
        known_safe_locations=[],
        usual_routes=[],
    )

    result = compute_risk_score(
        risk_input,
        stationary_minutes=data.stationary_minutes,
    )

    return {
        "risk_score": result.total_score,
        "risk_band": result.band,
        "factors": result.factors,
        "explanation": result.explanation,
        "alert": result.should_alert_contacts,
    }


# -----------------------------
# Real location update
# -----------------------------

@app.post("/location/update")
def update_location(data: RealLocationRequest):
    user_name = data.user.strip() or "Unknown User"

    speed_kmh = data.speed or 0
    vehicle = detect_vehicle(speed_kmh)

    if user_name not in users:
        users[user_name] = {
            "user": user_name,
            "started_at": now_iso(),
            "route": []
        }

    users[user_name].update({
        "lat": data.lat,
        "lng": data.lng,
        "permission": data.permission,
        "permission_time": data.permission_time,
        "last_seen": now_iso(),
        "status": "ONLINE",
        "speed": speed_kmh,
        "accuracy": data.accuracy,
        "battery": data.battery,
        "vehicle": vehicle,
    })

    # Only store route points if accuracy is acceptable
    if data.accuracy <= 100:
        users[user_name]["route"].append([data.lat, data.lng])

    # Persist the location point into Supabase
    if SUPABASE_CLIENT is not None:
        try:
            if users[user_name].get("session_id") is None:
                session_resp = SUPABASE_CLIENT.table("tracking_sessions").insert({
                    "user_name": user_name,
                    "permission": data.permission,
                    "status": "ONLINE"
                }).execute()
                session_data = getattr(session_resp, "data", None) or (session_resp.get("data") if isinstance(session_resp, dict) else None)
                if session_data and isinstance(session_data, list) and len(session_data) > 0:
                    users[user_name]["session_id"] = session_data[0].get("id")

            risk = calculate_real_risk(users[user_name])
            insert_location_point(SUPABASE_CLIENT, {
                "session_id": users[user_name].get("session_id"),
                "user_name": user_name,
                "lat": data.lat,
                "lng": data.lng,
                "speed": speed_kmh,
                "accuracy": data.accuracy,
                "battery": str(data.battery),
                "vehicle": vehicle,
                "risk_score": int(risk.get("risk_score", 0)),
                "risk_band": risk.get("risk_band", "SAFE")
            })
            upsert_user_profile(SUPABASE_CLIENT, {
                "name": user_name
            })
        except Exception:
            pass

    return {
        "message": "Location updated",
        "user": users[user_name]
    }


@app.get("/location/latest")
def get_latest_location():
    if not users:
        return {
            "message": "No active users",
            "users": []
        }

    output = []

    for user in users.values():
        online = is_user_online(user.get("last_seen"))

        user["status"] = "ONLINE" if online else "OFFLINE / PAGE CLOSED"
        user["real_risk"] = calculate_real_risk(user)

        output.append(user)

    return {
        "total_users": len(output),
        "users": output
    }


@app.get("/tracking/sessions")
def get_tracking_sessions():
    output = []

    for user in users.values():
        online = is_user_online(user.get("last_seen"))

        route = user.get("route", [])
        start_location = route[0] if route else None
        end_location = route[-1] if route else None

        output.append({
            "user": user.get("user"),
            "permission": user.get("permission"),
            "permission_time": user.get("permission_time"),
            "started_at": user.get("started_at"),
            "last_seen": user.get("last_seen"),
            "status": "ONLINE" if online else "OFFLINE / PAGE CLOSED",
            "vehicle": user.get("vehicle"),
            "speed": user.get("speed"),
            "accuracy": user.get("accuracy"),
            "battery": user.get("battery", "Unknown"),
            "route_points": len(route),
            "start_location": start_location,
            "end_location": end_location,
            "total_distance_km": calculate_total_distance(route),
            "risk": calculate_real_risk(user)
        })

    return output


@app.get("/risk/live")
def live_risk():
    results = []
    for user in users.values():
        risk = calculate_real_risk(user)
        results.append({
            "user": user.get("user"),
            "status": user.get("status"),
            "battery": user.get("battery"),
            "vehicle": user.get("vehicle"),
            "speed": user.get("speed"),
            "risk": risk
        })

    return {
        "total_users": len(results),
        "results": results
    }


@app.get("/tracking/history")
def get_tracking_history():
    history = []

    for user in users.values():
        route = user.get("route", [])
        if not route:
            continue

        for index, point in enumerate(route):
            history.append({
                "user": user.get("user"),
                "lat": point[0],
                "lng": point[1],
                "timestamp": user.get("started_at") if index == 0 else user.get("last_seen")
            })

    return {
        "history": history
    }


# -----------------------------
# Demo timeline
# -----------------------------

@app.get("/demo/timeline")
def demo_timeline():
    timeline = [
        {
            "time": "10:00 PM",
            "event": "Safety Mode Started",
            "description": "User enabled consent-based location sharing.",
            "risk_score": 0,
            "risk_band": "SAFE"
        },
        {
            "time": "10:02 PM",
            "event": "Movement Detected",
            "description": "User is moving normally.",
            "risk_score": 0,
            "risk_band": "SAFE"
        },
        {
            "time": "10:05 PM",
            "event": "Battery Warning",
            "description": "Battery dropped below 15%.",
            "risk_score": 20,
            "risk_band": "WATCH"
        },
        {
            "time": "10:07 PM",
            "event": "Sudden Stop",
            "description": "User was moving fast and suddenly stopped.",
            "risk_score": 40,
            "risk_band": "WATCH"
        },
        {
            "time": "10:09 PM",
            "event": "Repeated SOS",
            "description": "User triggered SOS multiple times.",
            "risk_score": 80,
            "risk_band": "DANGER"
        },
        {
            "time": "10:10 PM",
            "event": "Emergency Alert Sent",
            "description": "Trusted contacts should be notified immediately.",
            "risk_score": 100,
            "risk_band": "DANGER"
        }
    ]

    return {
        "user_id": "demo_user",
        "mode": "LIVE_EMERGENCY_SIMULATION",
        "timeline": timeline
    }


@app.get("/simulate")
def simulate():
    scenarios = [
        {
            "name": "SAFE",
            "data": {
                "user_id": "sim_safe",
                "lat": 17.3850,
                "lng": 78.4867,
                "speed_kmh": 25,
                "previous_speed_kmh": 25,
                "battery_percent": 80,
                "sos_triggers_last_30min": 0,
                "stationary_minutes": 0,
                "hour": 14
            }
        },
        {
            "name": "WATCH",
            "data": {
                "user_id": "sim_watch",
                "lat": 17.3850,
                "lng": 78.4867,
                "speed_kmh": 5,
                "previous_speed_kmh": 10,
                "battery_percent": 10,
                "sos_triggers_last_30min": 0,
                "stationary_minutes": 0,
                "hour": 20
            }
        },
        {
            "name": "DANGER",
            "data": {
                "user_id": "sim_danger",
                "lat": 17.3850,
                "lng": 78.4867,
                "speed_kmh": 0,
                "previous_speed_kmh": 30,
                "battery_percent": 10,
                "sos_triggers_last_30min": 2,
                "stationary_minutes": 15,
                "hour": 23
            }
        }
    ]

    scenario = random.choice(scenarios)
    risk_request = RiskRequest(**scenario["data"])

    return {
        "scenario": scenario["name"],
        "ai_result": check_risk(risk_request)
    }
