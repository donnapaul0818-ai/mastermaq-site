from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import asyncio
import logging
import bcrypt
import jwt
import requests
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import Optional, Any
import uuid
import random
import string
from html import escape

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_ALGORITHM = "HS256"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────
def get_jwt_secret():
    return os.environ["JWT_SECRET"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(minutes=60), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def generate_os_number():
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"OS-{date_part}-{random_part}"

# ── Pydantic Models ─────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    phone: str = ""
    phone2: str = ""
    cep: str = ""
    address: str = ""
    number: str = ""
    complement: str = ""
    reference_point: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class ServiceOrderCreate(BaseModel):
    equipment_type: str
    brand: str
    service_type: str
    model: str = ""
    serial_number: str = ""
    warranty_status: str = ""
    defect_description: str = ""

class ContactCreate(BaseModel):
    name: str
    email: str
    phone: str = ""
    message: str

class BlogArticleCreate(BaseModel):
    title: str
    slug: str
    content: str
    summary: str = ""
    category: str = ""

# ── Static Data ──────────────────────────────────────────────────────
EQUIPMENT_TYPES = [
    {"id": "geladeiras", "name": "Geladeiras", "icon": "Snowflake"},
    {"id": "trituradores", "name": "Trituradores", "icon": "Cog"},
    {"id": "lava-e-seca", "name": "Lava e Seca", "icon": "Shirt"},
    {"id": "lavadoras", "name": "Lavadoras", "icon": "Droplets"},
    {"id": "lava-loucas", "name": "Lava Louças", "icon": "Utensils"},
    {"id": "ar-condicionado-split", "name": "Ar Condicionado Split", "icon": "Wind"},
    {"id": "ar-condicionado-portatil", "name": "Ar Condicionado Portatil", "icon": "AirVent"},
    {"id": "vrf-hisense", "name": "VRF Hisense", "icon": "Server"},
    {"id": "freezers", "name": "Freezers", "icon": "Thermometer"},
    {"id": "coifas", "name": "Coifas", "icon": "Fan"},
    {"id": "forno-eletrico", "name": "Forno Elétrico", "icon": "ChefHat"},
    {"id": "microondas", "name": "Microondas", "icon": "Microwave"},
    {"id": "frigobar", "name": "Frigobar", "icon": "Refrigerator"},
    {"id": "maquina-de-gelo", "name": "Máquina de Gelo", "icon": "IceCream"},
    {"id": "cervejeira", "name": "Cervejeira", "icon": "Beer"},
]

BRANDS = ["Panasonic", "Liebherr", "Bertazzoni", "Hisense", "Invisacook", "Viking", "Daikin", "Elettromec", "Tecno", "Samsung", "LG", "Brastemp", "Electrolux", "Bosch", "Consul", "Midea", "Philco"]

INSTALLATION_DISABLED = ["geladeiras", "ar-condicionado-portatil", "lava-e-seca", "lavadoras"]

# ── Auth Endpoints ───────────────────────────────────────────────────
@api_router.post("/auth/register")
async def register(data: RegisterRequest, response: Response):
    email = data.email.lower().strip()
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    # Phone is required because the external OS system (Mastermaq Systems)
    # refuses payloads without phone1. Without this, every OS created by the
    # user would silently fail to sync.
    phone_digits = "".join(ch for ch in (data.phone or "") if ch.isdigit())
    if len(phone_digits) < 10:
        raise HTTPException(status_code=400, detail="Telefone é obrigatório (com DDD)")
    if not (data.name or "").strip():
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_doc = {
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "phone": data.phone,
        "phone2": data.phone2,
        "cep": data.cep,
        "address": data.address,
        "number": data.number,
        "complement": data.complement,
        "reference_point": data.reference_point,
        "neighborhood": data.neighborhood,
        "city": data.city,
        "state": data.state,
        "role": "customer",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=2592000, path="/")
    full = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    full["_id"] = str(full["_id"])
    try:
        asyncio.create_task(email_welcome(email, data.name))
    except Exception:
        pass
    return full
    full["_id"] = str(full["_id"])
    return full

@api_router.post("/auth/login")
async def login(data: LoginRequest, request: Request, response: Response):
    email = data.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        locked = attempt.get("locked_until")
        if locked and datetime.now(timezone.utc) < datetime.fromisoformat(locked):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}},
            upsert=True
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=2592000, path="/")
    full = await db.users.find_one({"_id": user["_id"]}, {"password_hash": 0})
    full["_id"] = str(full["_id"])
    return full

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


# ── Google OAuth (One-Tap / Sign-in with Google id_token verification) ─────
class GoogleAuthRequest(BaseModel):
    credential: str  # JWT id_token returned by Google Identity Services


@api_router.post("/auth/google")
async def google_auth(data: GoogleAuthRequest, response: Response):
    """Verifies a Google ID token returned by the front-end "Sign in with
    Google" button and emits the same httpOnly cookie pair as email/password
    login. First-time logins create a new user; subsequent logins update the
    Google profile fields.

    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    """
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not google_client_id:
        raise HTTPException(status_code=500, detail="Google OAuth não configurado")
    try:
        from google.oauth2 import id_token as _id_token
        from google.auth.transport import requests as _g_requests
        idinfo = _id_token.verify_oauth2_token(
            data.credential,
            _g_requests.Request(),
            google_client_id,
        )
    except ValueError as e:
        logger.warning(f"[google-auth] invalid token: {e}")
        raise HTTPException(status_code=401, detail="Token Google inválido")
    except Exception as e:
        logger.error(f"[google-auth] verify err: {e}")
        raise HTTPException(status_code=500, detail="Falha ao validar token Google")

    email = (idinfo.get("email") or "").lower().strip()
    if not email or not idinfo.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email Google não verificado")

    google_sub = idinfo.get("sub")
    name = idinfo.get("name") or ""
    picture = idinfo.get("picture") or ""

    existing = await db.users.find_one({"email": email})
    if existing:
        # Link the Google identity to the existing email account.
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "google_sub": google_sub,
                "google_picture": picture,
                "name": existing.get("name") or name,
                "auth_provider": existing.get("auth_provider") or "google",
            }}
        )
        user_id = str(existing["_id"])
    else:
        # First-time Google sign-in: create a new customer record. Password is
        # left empty — the user can only sign in via Google until they set a
        # password through password reset.
        doc = {
            "email": email,
            "password_hash": "",
            "name": name,
            "phone": "",
            "cep": "",
            "address": "",
            "number": "",
            "neighborhood": "",
            "city": "",
            "state": "",
            "role": "customer",
            "auth_provider": "google",
            "google_sub": google_sub,
            "google_picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await db.users.insert_one(doc)
        user_id = str(result.inserted_id)

    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=2592000, path="/")
    full = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    full["_id"] = str(full["_id"])
    return full

@api_router.get("/auth/me")
async def get_me(request: Request):
    return await get_current_user(request)

@api_router.post("/auth/refresh")
async def refresh_token_endpoint(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = str(user["_id"])
        new_access = create_access_token(user_id, user["email"])
        response.set_cookie(key="access_token", value=new_access, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@api_router.put("/auth/profile")
async def update_profile(request: Request):
    user = await get_current_user(request)
    body = await request.json()
    allowed = ["name", "phone", "phone2", "cep", "address", "number", "complement", "reference_point", "neighborhood", "city", "state"]
    update_data = {k: v for k, v in body.items() if k in allowed}
    if update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": update_data})
    updated = await db.users.find_one({"_id": ObjectId(user["_id"])}, {"password_hash": 0})
    updated["_id"] = str(updated["_id"])
    return updated

# ── Equipment ────────────────────────────────────────────────────────
@api_router.get("/equipment/types")
async def get_equipment_types():
    return EQUIPMENT_TYPES

@api_router.get("/equipment/brands")
async def get_brands():
    return BRANDS

@api_router.get("/equipment/rules")
async def get_rules():
    return {"installation_disabled": INSTALLATION_DISABLED}

# ── Supabase (external system DB — single source of truth for OS) ────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Fields NOT shown to the customer in "Ver Detalhes" (laudo/técnico/internos)
OS_EXCLUDED_FIELDS = {
    "priority", "status_orcamento", "conclusao_orcamento", "technical_diagnosis",
    "required_parts", "installation_correct", "technician",
    "voltage_f1f2", "voltage_f1_terra", "voltage_f2_terra",
    "photo_1", "photo_2", "photo_3", "photo_4", "photo_5",
    "photo_6", "photo_7", "photo_8", "photo_9",
    "signature_customer", "signature_technician", "signature_client",
    "signature_client_name", "signature_client_cpf", "signature_date", "signature_tech_name",
    "assinafy_status", "assinafy_document_id", "scheduling_history",
    "print_count", "share_token", "sort_date", "lat", "lng", "id", "batch", "micro_status",
}

# Fields the CUSTOMER may edit on their own OS
OS_CUSTOMER_EDITABLE = {
    "customer_name", "email", "cep", "address", "number", "neighborhood",
    "city", "state", "complement", "reference_point", "phone1",
}


def _sb_headers(extra: dict = None):
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


async def _sb_request(method: str, path: str, params: dict = None, json_body=None, headers_extra: dict = None):
    """Run a PostgREST call against Supabase in a thread (requests is sync)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    url = f"{SUPABASE_URL}/rest/v1/{path}"

    def _do():
        import requests as _req
        return _req.request(
            method, url, params=params, json=json_body,
            headers=_sb_headers(headers_extra), timeout=15,
        )
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _do)
    return resp


async def sb_get_orders_by_email(email: str) -> list:
    email = (email or "").strip()
    if not email:
        return []
    # ilike (no wildcards) = case-insensitive exact match
    resp = await _sb_request(
        "GET", "service_orders",
        params={
            "email": f"ilike.{email}",
            "select": "*",
            "order": "created_at.desc",
            "limit": "200",
        },
    )
    if resp.status_code != 200:
        logger.warning(f"[supabase] list by email failed {resp.status_code}: {resp.text[:200]}")
        return []
    try:
        return resp.json()
    except Exception:
        return []


async def sb_get_order(os_number: str) -> Optional[dict]:
    resp = await _sb_request(
        "GET", "service_orders",
        params={"os_number": f"eq.{os_number}", "select": "*", "limit": "1"},
    )
    if resp.status_code != 200:
        return None
    try:
        rows = resp.json()
        return rows[0] if rows else None
    except Exception:
        return None


async def sb_update_order(os_number: str, fields: dict) -> Optional[dict]:
    fields = dict(fields)
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    resp = await _sb_request(
        "PATCH", "service_orders",
        params={"os_number": f"eq.{os_number}"},
        json_body=fields,
        headers_extra={"Prefer": "return=representation"},
    )
    if resp.status_code not in (200, 204):
        logger.warning(f"[supabase] update failed {resp.status_code}: {resp.text[:200]}")
        raise HTTPException(status_code=502, detail="Falha ao atualizar OS no sistema")
    try:
        rows = resp.json()
        return rows[0] if rows else None
    except Exception:
        return None


def _normalize_os_for_card(row: dict) -> dict:
    """Slim view used in the portal list / cards."""
    return {
        "os_number": row.get("os_number"),
        "external_os_number": row.get("os_number"),
        "product": row.get("product"),
        "equipment_type": row.get("product"),
        "brand": row.get("brand"),
        "service_type": row.get("service_type"),
        "status": row.get("status"),
        "sub_status": row.get("sub_status"),
        "created_at": row.get("created_at") or row.get("registration_date"),
        "defect_description": row.get("reported_defect"),
        "model": row.get("model"),
    }


def _normalize_os_detail(row: dict) -> dict:
    """Full detail view minus técnico/laudo fields; adds friendly aliases."""
    out = {k: v for k, v in row.items() if k not in OS_EXCLUDED_FIELDS}
    out["equipment_type"] = row.get("product")
    out["defect_description"] = row.get("reported_defect")
    out["external_os_number"] = row.get("os_number")
    return out


# ── Service Orders ───────────────────────────────────────────────────
def _service_type_external_label(st: str, warranty_status: str = "") -> str:
    """Map internal service to the external API expected labels.

    Per business rules (May 2026):
      - Inside warranty  -> "Garantia"
      - Outside warranty -> "Orçamento"
    The concrete operation (conserto/instalação/manutenção) goes to
    observations, NOT to service_type. We default to "Orçamento" when
    warranty status is missing.
    """
    w = (warranty_status or "").lower().strip()
    if w in ("dentro", "dentro_garantia", "garantia", "em_garantia"):
        return "Garantia"
    return "Orçamento"


def _service_operation_label(st: str) -> str:
    """Human label for the operation: used in observations only."""
    m = {
        "conserto": "Conserto",
        "orcamento": "Orçamento",
        "instalacao": "Instalação",
        "manutencao": "Manutenção",
    }
    return m.get((st or "").lower(), (st or "").capitalize() or "Conserto")


def _equipment_name(eq_id: str) -> str:
    for eq in EQUIPMENT_TYPES:
        if eq.get("id") == eq_id:
            return eq.get("name", eq_id)
    return eq_id or ""


async def _push_to_external_system(order_doc: dict, user_doc: Optional[dict]) -> dict:
    """Send OS to the Mastermaq Systems external API. Non-blocking style errors
    are swallowed but returned for logging; does not raise."""
    url = os.environ.get("EXTERNAL_OS_API_URL", "")
    key = os.environ.get("EXTERNAL_OS_API_KEY", "")
    if not url or not key:
        return {"ok": False, "error": "external_api_not_configured"}

    def _digits(v): return "".join(ch for ch in (v or "") if ch.isdigit())

    # Build payload from both order and user profile. Per business rules:
    #   - `service_type` carries warranty kind only: "Garantia" | "Orçamento".
    #   - The actual operation (Conserto / Instalação) goes to `observations`.
    user = user_doc or {}
    operation = _service_operation_label(order_doc.get("service_type", ""))
    warranty_label = "Dentro da garantia" if (order_doc.get("warranty_status", "") or "").lower().startswith("dentro") else "Fora da garantia"
    defect_text = (order_doc.get("defect_description") or "").strip()
    observation_parts = [
        f"Tipo de serviço: {operation}",
        f"Garantia: {warranty_label}",
        f"OS interna: {order_doc.get('os_number', '')}",
        "Origem: site Mastermaq",
    ]
    if defect_text:
        observation_parts.append(f"Defeito relatado: {defect_text}")

    phone_digits = _digits(user.get("phone") or order_doc.get("user_phone") or "")
    phone2_digits = _digits(user.get("phone2") or "")
    payload = {
        "customer_name": order_doc.get("user_name") or user.get("name") or "Cliente Site",
        "phone1": phone_digits,
        "phone2": phone2_digits or phone_digits,
        "address": user.get("address") or "",
        "number": user.get("number") or "",
        "neighborhood": user.get("neighborhood") or "",
        "city": user.get("city") or "Belo Horizonte",
        "state": user.get("state") or "MG",
        "cep": _digits(user.get("cep") or ""),
        "email": order_doc.get("user_email") or user.get("email") or "",
        "product": _equipment_name(order_doc.get("equipment_type", "")),
        "brand": order_doc.get("brand") or "",
        "model": order_doc.get("model") or "",
        "serial_number": order_doc.get("serial_number") or "",
        "reported_defect": defect_text,
        "observations": " | ".join(observation_parts),
        "service_type": _service_type_external_label(
            order_doc.get("service_type", ""),
            order_doc.get("warranty_status", ""),
        ),
        "reference_point": user.get("reference_point") or "",
        "complement": user.get("complement") or "",
        "source": "site",
        "visit_fee": "150.0",
    }
    # Require customer_name and phone1 per external spec
    if not payload["customer_name"] or not payload["phone1"]:
        return {"ok": False, "error": "missing_required", "payload": payload}

    try:
        def _post():
            import requests as _req
            return _req.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": key,
                },
                timeout=12,
            )
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, _post)
        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:300]}
        return {"ok": resp.status_code in (200, 201), "status_code": resp.status_code, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def _sync_order_to_external(os_number: str, order_doc: dict, user_doc: Optional[dict]):
    """Background task: push the OS to the external Mastermaq Systems API and
    persist the outcome on the local document. Any error is swallowed — the
    local OS is already created and the user already got their confirmation."""
    try:
        ext = await _push_to_external_system(order_doc, user_doc)
        external_os = None
        if ext.get("ok") and isinstance(ext.get("data"), dict):
            external_os = ext["data"].get("os_number") or ext["data"].get("id")
        # Explicit log so we can diagnose sync issues in production from the
        # backend logs alone (without having to dump Mongo).
        if ext.get("ok"):
            logger.info(f"[ext-sync] OK {os_number} -> external={external_os}")
        else:
            logger.warning(
                f"[ext-sync] FAIL {os_number} error={ext.get('error')} "
                f"status={ext.get('status_code')} payload_name={bool(ext.get('payload',{}).get('customer_name'))} "
                f"payload_phone={bool(ext.get('payload',{}).get('phone1'))}"
            )
        await db.service_orders.update_one(
            {"os_number": os_number},
            {"$set": {
                "external_os_number": external_os,
                "external_status": (ext.get("data") or {}).get("status") if isinstance(ext.get("data"), dict) else None,
                "external_sync_ok": bool(ext.get("ok")),
                "external_sync_error": None if ext.get("ok") else (ext.get("error") or f"HTTP {ext.get('status_code')}"),
                "external_synced_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
    except Exception as e:
        logger.warning(f"external sync background err: {e}")


@api_router.post("/service-orders", status_code=201)
async def create_service_order(data: ServiceOrderCreate, request: Request):
    """Create an OS by pushing to the external Mastermaq Systems API, which
    assigns the sequential number and persists it in Supabase (single source
    of truth). The site only READS from Supabase afterwards."""
    user = await get_current_user(request)  # login required
    user_doc = dict(user)

    # Gate: complete profile (name + phone) required for the external API.
    phone_digits = "".join(ch for ch in (user_doc.get("phone") or "") if ch.isdigit())
    if len(phone_digits) < 10 or not (user_doc.get("name") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Complete seu perfil (nome e telefone) antes de abrir uma OS.",
        )

    order_doc = {
        "os_number": "",
        "user_email": user_doc.get("email"),
        "user_name": user_doc.get("name"),
        "equipment_type": data.equipment_type,
        "brand": data.brand,
        "service_type": data.service_type,
        "model": data.model,
        "serial_number": data.serial_number,
        "warranty_status": data.warranty_status,
        "defect_description": data.defect_description,
    }
    user_snapshot = dict(user_doc)
    user_snapshot.pop("_id", None)
    user_snapshot.pop("password_hash", None)

    ext = await _push_to_external_system(order_doc, user_snapshot)
    if not ext.get("ok"):
        logger.warning(f"[create-os] external push failed: {ext.get('error')} status={ext.get('status_code')}")
        raise HTTPException(status_code=502, detail="Não foi possível registrar a OS no sistema. Tente novamente.")

    ext_data = ext.get("data") if isinstance(ext.get("data"), dict) else {}
    external_os = str(ext_data.get("os_number") or ext_data.get("id") or "")

    # Fire-and-forget confirmation email (best-effort).
    try:
        asyncio.create_task(email_order_confirmation(
            user_doc.get("email"), user_doc.get("name"), external_os,
            _equipment_name(data.equipment_type), data.brand,
        ))
    except Exception:
        pass

    return {
        "os_number": external_os,
        "external_os_number": external_os,
        "product": _equipment_name(data.equipment_type),
        "equipment_type": _equipment_name(data.equipment_type),
        "brand": data.brand,
        "service_type": _service_type_external_label(data.service_type, data.warranty_status),
        "status": "Aguardando Analise A.T",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

@api_router.get("/service-orders")
async def list_service_orders(request: Request):
    """List the logged-in customer's OS from Supabase (matched by email)."""
    user = await get_current_user(request)
    rows = await sb_get_orders_by_email(user.get("email") or "")
    return [_normalize_os_for_card(r) for r in rows]


@api_router.post("/admin/service-orders/resync")
async def admin_resync_failed_orders(request: Request, background_tasks: BackgroundTasks, limit: int = 100):
    """Admin-only: re-queue every local OS that failed to sync with the
    external Mastermaq Systems API. Returns a summary with counts and the
    list of OS numbers scheduled for retry. Actual retry happens in the
    background via BackgroundTasks."""
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    query = {"$or": [{"external_sync_ok": False}, {"external_sync_ok": None}, {"external_os_number": None}]}
    cursor = db.service_orders.find(query).sort("created_at", -1).limit(max(1, min(500, limit)))
    to_retry = []
    async for o in cursor:
        owner = None
        uid = o.get("user_id")
        if uid:
            # user_id is stored as string (ObjectId.__str__), so look up by that
            # and fall back to a raw ObjectId match only if needed.
            owner = await db.users.find_one({"_id": uid})
            if not owner:
                try:
                    from bson import ObjectId as _OID
                    owner = await db.users.find_one({"_id": _OID(uid)})
                except Exception:
                    owner = None
            if owner:
                owner.pop("password_hash", None)
        snapshot = dict(o); snapshot.pop("_id", None)
        if owner:
            owner.pop("_id", None)
        background_tasks.add_task(_sync_order_to_external, o["os_number"], snapshot, owner)
        to_retry.append({
            "os_number": o["os_number"],
            "previous_error": o.get("external_sync_error"),
            "created_at": o.get("created_at"),
        })
    return {"queued": len(to_retry), "orders": to_retry}

@api_router.get("/service-orders/{os_number}")
async def get_service_order(os_number: str, request: Request):
    """Full OS detail from Supabase (minus técnico/laudo fields). Only the
    owner (email match) or an admin may view it."""
    user = await get_current_user(request)
    row = await sb_get_order(os_number)
    if not row:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    owner_email = (row.get("email") or "").strip().lower()
    user_email = (user.get("email") or "").strip().lower()
    if user.get("role") != "admin" and owner_email and owner_email != user_email:
        raise HTTPException(status_code=403, detail="Acesso negado a esta OS")
    return _normalize_os_detail(row)


class ServiceOrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    email: Optional[str] = None
    cep: Optional[str] = None
    address: Optional[str] = None
    number: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    complement: Optional[str] = None
    reference_point: Optional[str] = None
    phone1: Optional[str] = None


@api_router.put("/service-orders/{os_number}")
async def update_service_order(os_number: str, data: ServiceOrderUpdate, request: Request):
    """Customer edits allowed fields on a single OS directly in Supabase."""
    user = await get_current_user(request)
    row = await sb_get_order(os_number)
    if not row:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    owner_email = (row.get("email") or "").strip().lower()
    user_email = (user.get("email") or "").strip().lower()
    if user.get("role") != "admin" and owner_email and owner_email != user_email:
        raise HTTPException(status_code=403, detail="Acesso negado a esta OS")

    incoming = {k: v for k, v in data.dict().items() if v is not None and k in OS_CUSTOMER_EDITABLE}
    if not incoming:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")

    updated = await sb_update_order(os_number, incoming)
    if updated:
        return _normalize_os_detail(updated)
    row2 = await sb_get_order(os_number)
    return _normalize_os_detail(row2 or row)


# ── Payments (Mercado Pago Checkout Pro) ────────────────────────────
MP_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
MP_PUBLIC_KEY = os.environ.get("MERCADOPAGO_PUBLIC_KEY", "").strip()
MP_WEBHOOK_SECRET = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
MP_API = "https://api.mercadopago.com"


def _mp_configured() -> bool:
    return bool(MP_ACCESS_TOKEN)


def _parse_fee(raw) -> float:
    try:
        v = float(str(raw).replace(",", ".").strip())
        return round(v, 2) if v > 0 else 0.0
    except Exception:
        return 0.0


ONE_REAL_EMAILS = {"donna.paul0818@gmail.com"}
MM_ORIGIN = (-19.8884857, -43.9395873)  # R. Descalvado, 636A - Renascença, BH
_OSM_HEADERS = {"User-Agent": "Mastermaq/1.0 (mastermaqassistencia@gmail.com)"}


def _is_bh(city: str) -> bool:
    import unicodedata
    c = unicodedata.normalize("NFKD", city or "").encode("ascii", "ignore").decode().lower().strip()
    return c in ("belo horizonte", "bh")


def _fee_for_km(km: float) -> float:
    if km <= 60:
        return 150.0
    return round(200.0 * km / 60.0, 2)


async def _road_km(row: dict) -> Optional[float]:
    addr_key = "|".join(str(row.get(k) or "").strip().lower() for k in ("cep", "address", "number", "neighborhood", "city", "state"))
    cached = await db.fee_cache.find_one({"key": addr_key})
    if cached:
        return cached.get("km")

    def _do():
        import requests as _req
        lat, lng = row.get("lat"), row.get("lng")
        if not (lat and lng):
            queries = [
                {"street": f"{row.get('number') or ''} {row.get('address') or ''}".strip(), "city": row.get("city") or "", "state": row.get("state") or "MG", "country": "Brasil"},
                {"q": f"{row.get('city') or ''}, {row.get('state') or 'MG'}, Brasil"},
            ]
            for q in queries:
                r = _req.get("https://nominatim.openstreetmap.org/search", params={**q, "format": "json", "limit": 1}, headers=_OSM_HEADERS, timeout=10)
                if r.ok and r.json():
                    lat, lng = r.json()[0]["lat"], r.json()[0]["lon"]
                    break
        if not (lat and lng):
            return None
        r = _req.get(f"https://router.project-osrm.org/route/v1/driving/{MM_ORIGIN[1]},{MM_ORIGIN[0]};{lng},{lat}", params={"overview": "false"}, timeout=10)
        if not r.ok or not r.json().get("routes"):
            return None
        return round(r.json()["routes"][0]["distance"] / 1000.0, 1)

    try:
        km = await asyncio.get_event_loop().run_in_executor(None, _do)
    except Exception as e:
        logger.warning(f"[fee] distance lookup failed: {e}")
        km = None
    if km is not None:
        await db.fee_cache.update_one({"key": addr_key}, {"$set": {"key": addr_key, "km": km}}, upsert=True)
    return km


async def _compute_visit_fee(row: dict, user_email: str = "") -> dict:
    emails = {(row.get("email") or "").strip().lower(), (user_email or "").strip().lower()}
    if emails & ONE_REAL_EMAILS:
        return {"amount": 1.0, "rule": "teste"}
    fixed = _parse_fee(row.get("visit_fee"))
    if fixed > 0:
        return {"amount": fixed, "rule": "sistema"}
    if _is_bh(row.get("city")):
        return {"amount": 100.0, "rule": "bh"}
    km = await _road_km(row)
    if km is None:
        return {"amount": 150.0, "rule": "padrao"}
    return {"amount": _fee_for_km(km), "rule": "distancia", "km": km}


async def _mp_create_preference(payload: dict) -> dict:
    def _do():
        import requests as _req
        return _req.post(
            f"{MP_API}/checkout/preferences",
            json=payload,
            headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}", "Content-Type": "application/json"},
            timeout=15,
        )
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _do)
    if resp.status_code not in (200, 201):
        logger.warning(f"[mp] create preference failed {resp.status_code}: {resp.text[:200]}")
        raise HTTPException(status_code=502, detail="Falha ao iniciar pagamento no Mercado Pago")
    return resp.json()


async def _mp_get_payment(payment_id: str) -> dict:
    def _do():
        import requests as _req
        return _req.get(
            f"{MP_API}/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
            timeout=15,
        )
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _do)
    if resp.status_code != 200:
        return {}
    return resp.json()


async def _assert_os_owner(os_number: str, user: dict) -> dict:
    row = await sb_get_order(os_number)
    if not row:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    owner_email = (row.get("email") or "").strip().lower()
    user_email = (user.get("email") or "").strip().lower()
    if user.get("role") != "admin" and owner_email and owner_email != user_email:
        raise HTTPException(status_code=403, detail="Acesso negado a esta OS")
    return row


@api_router.post("/service-orders/{os_number}/checkout")
async def create_payment_checkout(os_number: str, request: Request):
    """Create a Mercado Pago Checkout Pro preference for the OS visit fee.
    Amount comes from the OS (Supabase) — never from the client."""
    user = await get_current_user(request)
    row = await _assert_os_owner(os_number, user)

    existing = await db.payments.find_one({"os_number": os_number})
    if existing and existing.get("status") == "approved":
        raise HTTPException(status_code=409, detail="Taxa de visita já paga")

    amount = (await _compute_visit_fee(row, user.get("email")))["amount"]
    back = f"{PUBLIC_APP_URL}/pagamento?os={os_number}"

    if not _mp_configured():
        # MODO SIMULADO — chaves do Mercado Pago ainda não configuradas.
        await db.payments.update_one(
            {"os_number": os_number},
            {"$set": {
                "os_number": os_number, "amount": amount, "status": "pending",
                "provider": "mock", "user_email": (user.get("email") or "").lower(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        return {
            "mock": True,
            "amount": amount,
            "init_point": f"{back}&mock=1",
            "preference_id": f"mock-{os_number}",
        }

    payload = {
        "items": [{
            "id": os_number, "title": f"Taxa de visita — OS {os_number}",
            "quantity": 1, "currency_id": "BRL", "unit_price": amount,
        }],
        "external_reference": os_number,
        "notification_url": f"{PUBLIC_APP_URL}/api/payments/webhook",
        "back_urls": {"success": back, "pending": back, "failure": back},
        "auto_return": "approved",
        "statement_descriptor": "MASTERMAQ",
        "payer": {"email": (user.get("email") or "")},
    }
    pref = await _mp_create_preference(payload)
    await db.payments.update_one(
        {"os_number": os_number},
        {"$set": {
            "os_number": os_number, "amount": amount, "status": "pending",
            "provider": "mercadopago", "mp_preference_id": pref.get("id"),
            "user_email": (user.get("email") or "").lower(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {
        "mock": False,
        "amount": amount,
        "preference_id": pref.get("id"),
        "init_point": pref.get("init_point") or pref.get("sandbox_init_point"),
    }


class BrickPaymentIn(BaseModel):
    payment_method_id: str
    token: Optional[str] = None
    installments: Optional[int] = None
    issuer_id: Optional[Any] = None
    payer: dict = {}
    transaction_details: Optional[dict] = None


def _pix_info(mp: dict) -> dict:
    tx = (mp.get("point_of_interaction") or {}).get("transaction_data") or {}
    return {
        "qr_code": tx.get("qr_code"),
        "qr_code_base64": tx.get("qr_code_base64"),
        "ticket_url": tx.get("ticket_url") or (mp.get("transaction_details") or {}).get("external_resource_url"),
    }


async def _mark_os_paid_in_supabase(os_number: str, amount, payment_id: str):
    """Append a payment note to that single OS (no schema change)."""
    pay = await db.payments.find_one({"os_number": os_number})
    if (pay or {}).get("supabase_marked"):
        return
    try:
        row = await sb_get_order(os_number) or {}
        stamp = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
        note = f"[SITE] Taxa de visita PAGA via Mercado Pago em {stamp} — R$ {float(amount or 0):.2f} (pagamento {payment_id})"
        obs = (row.get("observations") or "").strip()
        await sb_update_order(os_number, {"observations": f"{obs}\n{note}".strip()})
        await db.payments.update_one({"os_number": os_number}, {"$set": {"supabase_marked": True}})
    except Exception as e:
        logger.warning(f"[mp] could not mark OS {os_number} paid in Supabase: {e}")


async def _on_payment_update(os_number: str, mp: dict):
    status = mp.get("status", "pending")
    payment_id = str(mp.get("id"))
    prev = await db.payments.find_one({"os_number": os_number}) or {}
    upd = {
        "status": status, "mp_payment_id": payment_id,
        "status_detail": mp.get("status_detail"),
        "payment_method_id": mp.get("payment_method_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    info = _pix_info(mp)
    if info.get("qr_code") or info.get("ticket_url"):
        upd["instructions"] = info
    await db.payments.update_one({"os_number": os_number}, {"$set": upd}, upsert=True)
    if status == "approved" and prev.get("status") != "approved":
        await _mark_os_paid_in_supabase(os_number, mp.get("transaction_amount") or prev.get("amount"), payment_id)
        to = prev.get("user_email")
        if to:
            asyncio.create_task(email_payment_approved(to, os_number, prev.get("amount")))


@api_router.post("/service-orders/{os_number}/pay")
async def pay_os_brick(os_number: str, data: BrickPaymentIn, request: Request):
    """Process a Payment Brick submission. Amount always comes from the OS."""
    if not _mp_configured():
        raise HTTPException(status_code=503, detail="Pagamento indisponível no momento")
    user = await get_current_user(request)
    row = await _assert_os_owner(os_number, user)
    existing = await db.payments.find_one({"os_number": os_number}) or {}
    if existing.get("status") == "approved":
        raise HTTPException(status_code=409, detail="Taxa de visita já paga")

    amount = (await _compute_visit_fee(row, user.get("email")))["amount"]
    payer = dict(data.payer or {})
    payer.setdefault("email", user.get("email"))
    body = {
        "transaction_amount": amount,
        "description": f"Taxa de visita — OS {os_number}",
        "external_reference": os_number,
        "payment_method_id": data.payment_method_id,
        "payer": payer,
        "notification_url": f"{PUBLIC_APP_URL}/api/payments/webhook",
        "statement_descriptor": "MASTERMAQ",
    }
    if data.token:
        body["token"] = data.token
    if data.installments:
        body["installments"] = data.installments
    if data.issuer_id:
        body["issuer_id"] = int(data.issuer_id) if str(data.issuer_id).isdigit() else data.issuer_id
    if data.transaction_details:
        body["transaction_details"] = data.transaction_details

    await db.payments.update_one(
        {"os_number": os_number},
        {"$set": {"os_number": os_number, "amount": amount, "provider": "mercadopago",
                  "user_email": (user.get("email") or "").lower(),
                  "updated_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat(), "status": "unpaid"}},
        upsert=True,
    )

    def _do():
        import requests as _req
        return _req.post(
            f"{MP_API}/v1/payments", json=body, timeout=20,
            headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}", "Content-Type": "application/json",
                     "X-Idempotency-Key": str(uuid.uuid4())},
        )
    resp = await asyncio.get_event_loop().run_in_executor(None, _do)
    if resp.status_code not in (200, 201):
        logger.warning(f"[mp] payment failed {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(status_code=400, detail="O Mercado Pago recusou os dados do pagamento. Confira e tente novamente.")
    mp = resp.json()
    await _on_payment_update(os_number, mp)
    return {"id": mp.get("id"), "status": mp.get("status"), "status_detail": mp.get("status_detail"),
            "payment_method_id": mp.get("payment_method_id"), **_pix_info(mp)}


@api_router.get("/service-orders/{os_number}/payment-status")
async def get_payment_status(os_number: str, request: Request):
    user = await get_current_user(request)
    row = await _assert_os_owner(os_number, user)
    pay = await db.payments.find_one({"os_number": os_number}, {"_id": 0})
    fee = await _compute_visit_fee(row, user.get("email"))
    if not pay:
        return {"status": "unpaid", **fee}
    return {
        **fee,
        "status": pay.get("status", "unpaid"),
        "amount": pay.get("amount") if pay.get("status") == "approved" else fee["amount"],
        "provider": pay.get("provider"),
        "mp_payment_id": pay.get("mp_payment_id"),
        "payment_method_id": pay.get("payment_method_id"),
        "instructions": pay.get("instructions") if pay.get("status") in ("pending", "in_process") else None,
    }


@api_router.post("/payments/mock/{os_number}")
async def mock_confirm_payment(os_number: str, request: Request):
    """DEV-ONLY: simulate a payment result while Mercado Pago keys are not set."""
    if _mp_configured():
        raise HTTPException(status_code=400, detail="Mercado Pago configurado — simulação desabilitada")
    user = await get_current_user(request)
    await _assert_os_owner(os_number, user)
    body = await request.json()
    status = body.get("status", "approved")
    if status not in ("approved", "pending", "rejected"):
        status = "approved"
    await db.payments.update_one(
        {"os_number": os_number},
        {"$set": {"status": status, "provider": "mock", "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    if status == "approved":
        pay = await db.payments.find_one({"os_number": os_number})
        try:
            asyncio.create_task(email_payment_approved(user.get("email"), os_number, (pay or {}).get("amount")))
        except Exception:
            pass
    return {"status": status, "mock": True}


@api_router.post("/payments/webhook")
async def mp_webhook(request: Request):
    """Mercado Pago payment notification. Verifies signature (when secret set),
    fetches the real payment and updates the local payment record."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    payment_id = str((body.get("data") or {}).get("id") or request.query_params.get("data.id") or "")
    if body.get("type") not in ("payment", None) or not payment_id:
        return {"ok": True}

    # Optional signature verification
    if MP_WEBHOOK_SECRET:
        try:
            import hashlib as _hl, hmac as _hm, time as _t
            sig = request.headers.get("x-signature", "")
            req_id = request.headers.get("x-request-id", "")
            parts = dict(x.split("=", 1) for x in sig.split(",") if "=" in x)
            ts, received = parts.get("ts"), parts.get("v1")
            if not ts or not received or abs(int(_t.time()) - int(ts)) > 300:
                raise HTTPException(status_code=401, detail="assinatura inválida")
            manifest = f"id:{payment_id};request-id:{req_id};ts:{ts};"
            expected = _hm.new(MP_WEBHOOK_SECRET.encode(), manifest.encode(), _hl.sha256).hexdigest()
            if not _hm.compare_digest(expected, received):
                raise HTTPException(status_code=401, detail="assinatura inválida")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="assinatura inválida")

    payment = await _mp_get_payment(payment_id)
    os_number = payment.get("external_reference")
    if not os_number:
        return {"ok": True}
    await _on_payment_update(os_number, payment)
    logger.info(f"[mp-webhook] OS={os_number} payment={payment_id} status={payment.get('status')}")
    return {"ok": True}


@api_router.get("/payments/public-key")
async def mp_public_key():
    return {"public_key": MP_PUBLIC_KEY, "configured": _mp_configured()}


# ── Email (Resend) ───────────────────────────────────────────────────
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Mastermaq Assistência Técnica <nao-responda@mastermaqassistencia.com.br>")
COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "mastermaqassistencia@gmail.com")
_SITE = "https://mastermaqassistencia.com.br"


def _email_shell(title: str, body_html: str) -> str:
    return (
        '<table role="presentation" width="100%" style="background:#f1f5f9;padding:24px 0">'
        '<tr><td align="center">'
        '<table role="presentation" width="600" style="background:#ffffff;border:1px solid #e2e8f0;font-family:Arial,Helvetica,sans-serif">'
        '<tr><td style="background:#0f172a;padding:20px 28px">'
        '<span style="color:#fff;font-size:18px;font-weight:bold">Mastermaq Assistência Técnica</span></td></tr>'
        f'<tr><td style="padding:28px">'
        f'<h1 style="color:#0f172a;font-size:20px;margin:0 0 16px">{escape(title)}</h1>'
        f'{body_html}</td></tr>'
        '<tr><td style="padding:18px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px">'
        'Mastermaq Assistência Técnica · R. Descalvado, 636A - Renascença, BH/MG · (31) 3422-5293<br>'
        'Nunca pedimos senha ou dados de cartão por e-mail.</td></tr>'
        '</table></td></tr></table>'
    )


async def send_email(to: str, subject: str, html: str) -> bool:
    """Best-effort transactional email via Resend. Never raises to the caller."""
    if not RESEND_API_KEY or not to:
        return False
    payload = {"from": EMAIL_FROM, "to": [to], "subject": subject, "html": html,
               "reply_to": COMPANY_EMAIL}

    def _do():
        import requests as _req
        return _req.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            timeout=15,
        )
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, _do)
        ok = resp.status_code in (200, 201)
        if not ok:
            logger.warning(f"[email] send failed {resp.status_code}: {resp.text[:200]}")
        return ok
    except Exception as e:
        logger.warning(f"[email] error: {e}")
        return False


async def email_order_confirmation(to: str, name: str, os_number: str, product: str, brand: str):
    body = (
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Olá {escape(name or "cliente")}, '
        f'recebemos sua solicitação de atendimento.</p>'
        f'<table role="presentation" width="100%" style="margin:16px 0;border:1px solid #e2e8f0">'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Nº da OS</td>'
        f'<td style="padding:10px 14px;color:#0f172a;font-weight:bold;text-align:right">{escape(str(os_number))}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Produto</td>'
        f'<td style="padding:10px 14px;color:#0f172a;text-align:right">{escape(product or "-")}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Marca</td>'
        f'<td style="padding:10px 14px;color:#0f172a;text-align:right">{escape(brand or "-")}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Status</td>'
        f'<td style="padding:10px 14px;color:#b45309;text-align:right">Aguardando Análise A.T</td></tr></table>'
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Nossa Central vai analisar e entrar em contato. '
        f'Acompanhe pelo <a href="{_SITE}/minha-conta" style="color:#2563eb">seu portal</a>.</p>'
    )
    await send_email(to, f"OS {os_number} recebida — Mastermaq", _email_shell("Solicitação recebida", body))


async def email_payment_approved(to: str, os_number: str, amount):
    try:
        amt = f"R$ {float(amount):.2f}".replace(".", ",")
    except Exception:
        amt = "a taxa de visita"
    body = (
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Confirmamos o pagamento de <strong>{escape(amt)}</strong> '
        f'referente à taxa de visita da OS <strong>{escape(str(os_number))}</strong>.</p>'
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Sua visita técnica será agendada pela nossa equipe. '
        f'Acompanhe pelo <a href="{_SITE}/minha-conta" style="color:#2563eb">seu portal</a>.</p>'
    )
    await send_email(to, f"Pagamento aprovado — OS {os_number}", _email_shell("Pagamento aprovado", body))


async def email_welcome(to: str, name: str):
    body = (
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Olá {escape(name or "cliente")}, '
        f'sua conta na Mastermaq foi criada com sucesso!</p>'
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Pelo portal você pode solicitar atendimento, '
        f'acompanhar suas ordens de serviço e falar com a nossa assistente virtual.</p>'
        f'<p style="margin:18px 0"><a href="{_SITE}/minha-conta" '
        f'style="background:#2563eb;color:#fff;padding:12px 20px;text-decoration:none;font-size:14px">Acessar meu portal</a></p>'
    )
    await send_email(to, "Bem-vindo à Mastermaq Assistência Técnica", _email_shell("Conta criada", body))


async def email_contact_to_company(name: str, email: str, phone: str, message: str):
    body = (
        f'<p style="color:#334155;font-size:14px;line-height:1.6">Nova mensagem pelo formulário de contato:</p>'
        f'<table role="presentation" width="100%" style="margin:12px 0;border:1px solid #e2e8f0">'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Nome</td>'
        f'<td style="padding:10px 14px;color:#0f172a;text-align:right">{escape(name or "-")}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Email</td>'
        f'<td style="padding:10px 14px;color:#0f172a;text-align:right">{escape(email or "-")}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#64748b;font-size:12px">Telefone</td>'
        f'<td style="padding:10px 14px;color:#0f172a;text-align:right">{escape(phone or "-")}</td></tr></table>'
        f'<p style="color:#334155;font-size:14px;line-height:1.6"><strong>Mensagem:</strong><br>{escape(message or "")}</p>'
    )
    await send_email(COMPANY_EMAIL, f"Contato pelo site — {name or email}", _email_shell("Nova mensagem de contato", body))


# ── Blog ─────────────────────────────────────────────────────────────
@api_router.get("/blog")
async def list_articles():
    articles = await db.blog_articles.find({"published": True}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return articles

@api_router.get("/blog/{slug}")
async def get_article(slug: str):
    article = await db.blog_articles.find_one({"slug": slug}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@api_router.post("/blog")
async def create_article(data: BlogArticleCreate, request: Request):
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    doc = {
        "title": data.title,
        "slug": data.slug,
        "content": data.content,
        "summary": data.summary,
        "category": data.category,
        "author": user.get("name", "Admin"),
        "published": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.blog_articles.insert_one(doc)
    doc.pop("_id", None)
    return doc

# ── Contact ──────────────────────────────────────────────────────────
@api_router.post("/contact")
async def submit_contact(data: ContactCreate):
    doc = {
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "message": data.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.contact_messages.insert_one(doc)
    doc.pop("_id", None)
    try:
        asyncio.create_task(email_contact_to_company(data.name, data.email, data.phone, data.message))
    except Exception:
        pass
    return {"message": "Mensagem enviada com sucesso!", "data": doc}

# ── CEP Proxy ────────────────────────────────────────────────────────
@api_router.get("/cep/{cep}")
async def lookup_cep(cep: str):
    cep_clean = cep.replace("-", "").replace(".", "").strip()
    if len(cep_clean) != 8 or not cep_clean.isdigit():
        raise HTTPException(status_code=400, detail="CEP invalido")
    try:
        resp = requests.get(f"https://viacep.com.br/ws/{cep_clean}/json/", timeout=5)
        data = resp.json()
        if "erro" in data:
            raise HTTPException(status_code=404, detail="CEP nao encontrado")
        return data
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Servico de CEP indisponivel")

# ── Chat IA "Mi" ─────────────────────────────────────────────────────
import litellm
from fastapi.responses import StreamingResponse
import json as _json

MI_SYSTEM_PROMPT = """Voce e a "Mi", assistente virtual oficial da Mastermaq Assistencia Tecnica, em Belo Horizonte/MG.

IDIOMA OBRIGATORIO: SEMPRE responda em portugues do Brasil (pt-BR), com acentuacao correta. Nunca responda em ingles, espanhol ou qualquer outro idioma, mesmo que o usuario digite em outra lingua.

ESTILO DE RESPOSTA PARA CONVERSA POR VOZ:
- Use frases curtas (8-18 palavras, em media). Conversacional e natural, como se falasse pessoalmente.
- Evite listas e marcadores quando a pergunta for de voz: prefira frases corridas conectadas com "e", "alem disso", "tambem".
- NUNCA use **asteriscos**, _underscores_, # cabecalhos, links em markdown ou emojis nas respostas — eles atrapalham a leitura por voz.
- Pontue corretamente (virgulas, pontos finais, interrogacoes) para o motor de TTS conseguir entoar bem.
- Evite numeracoes longas. Quando precisar enumerar, fale "primeiro... depois... e por fim".

IDENTIDADE DA EMPRESA:
- Nome: Mastermaq Assistencia Tecnica
- Endereco: R. Descalvado, 636A - Renascenca, BH/MG, 31130-610
- Telefone: (31) 3422-5293
- Email: mastermaqassistencia@gmail.com
- Horario: Seg-Sex, 09:00 as 18:00
- Experiencia: 30+ anos, 28.000+ clientes atendidos, 4.1 estrelas no Google

MARCAS AUTORIZADAS (credenciamento oficial):
HQ (Belmicro), Franke, Hisense, Gorenje, Bertazzoni, Lofra, Panasonic, Liebherr, Invisacook (cooktops de inducao invisiveis), Viking, Daikin (Split, Multi Split, SkyAir, VRV), Elettromec, Tecno.
Tambem atendemos marcas gerais: Samsung, LG, Brastemp, Consul, Electrolux, Bosch, Midea, Philco.

EQUIPAMENTOS:
Geladeiras, Trituradores, Lava e Seca, Lavadoras, Ar Condicionado Split, Ar Condicionado Portatil, VRF Hisense, Freezers, Coifas.

INSTALACAO NAO DISPONIVEL para: Geladeiras, Ar Condicionado Portatil, Lava e Seca, Lavadoras.

COMO VOCE DEVE AGIR:
1. Seja cordial, objetiva e use linguagem brasileira natural com acentuacao correta.
2. Ajude com: informacoes da empresa, marcas atendidas, horarios, solicitacao de atendimento, status de OS, duvidas gerais sobre o servico.
3. NUNCA forneca diagnostico tecnico de problema em eletrodomestico. Se o cliente descrever um defeito (ex: "geladeira nao gela", "lavadora vaza agua"), voce deve:
   - Reconhecer o problema com empatia (1 linha).
   - Explicar que diagnostico preciso so pode ser feito presencialmente por tecnico habilitado, por seguranca e eficacia.
   - Recomendar abrir uma Ordem de Servico (OS) para que a Central de Atendimento avalie e organize a visita do tecnico.
   - Sugerir clicar em "Solicitar Orcamento" no site, ou ligar (31) 3422-5293, ou se logado, usar o portal "Minha Conta".

FLUXO CORRETO DE ATENDIMENTO (REGRA OBRIGATORIA):
A Mastermaq NAO oferece agendamento imediato pelo site ou pelo chat. O fluxo correto e:
   - O cliente abre uma Ordem de Servico (OS) pelo site, chat ou telefone (e uma SOLICITACAO de atendimento).
   - A Central de Atendimento da Mastermaq analisa a OS, valida os dados e cruza com o roteiro logistico e a agenda dos tecnicos.
   - A equipe entra em contato com o cliente em ate 1 dia util para confirmar a OS e combinar a melhor data e horario para a visita.

LINGUAGEM OBRIGATORIA:
- NUNCA diga "agendamento imediato", "agendar agora", "agende sua visita", "marcar horario na hora", "agendar visita tecnica" ou expressoes equivalentes que sugiram garantia de data/horario.
- SEMPRE prefira: "solicitar orcamento", "solicitar atendimento", "abrir uma OS", "abrir uma solicitacao de atendimento", "gerar a OS", "registrar sua solicitacao".
- Use frases como "Apos sua solicitacao, nossa equipe entra em contato para combinar a melhor data e horario".

4. Quando o cliente pedir uma visita tecnica, colete (se ele ainda nao informou): tipo de equipamento, marca, modelo, breve descricao do problema, e oriente a finalizar a SOLICITACAO pelo modal/formulario do site.

5. Quando o cliente pedir atendimento para um dia/data especifica (ex.: "amanha", "sexta-feira", "dia 28", "essa semana"):
   - Confirme a preferencia com gentileza, mas SEMPRE explique, em linguagem natural, que:
     a) Apos a abertura da OS, a Central de Atendimento ira analisar a solicitacao e verificar a disponibilidade dos tecnicos conforme o roteiro logistico do dia.
     b) O horario/data efetivos podem variar conforme a regiao e a agenda dos tecnicos.
     c) O cliente vai receber um contato da equipe para confirmar a OS e combinar o melhor horario assim que a solicitacao for analisada.
   - Nunca prometa data/horario garantidos. Use frases naturais, nao robotizadas (ex.: "Anotei sua preferencia para sexta. Assim que a OS for analisada, nossa Central de Atendimento entra em contato para confirmar e combinar o melhor horario com voce — pode variar um pouco dependendo da regiao.").

6. SOBRE PRODUTOS FORA DA GARANTIA (regra obrigatoria — SEMPRE informe quando o cliente disser que esta fora da garantia ou que e particular):
   - Para produtos fora da garantia, e cobrada uma TAXA DE DESLOCAMENTO e DIAGNOSTICO TECNICO.
   - Essa taxa nao se perde: ela e ABATIDA do valor total do orcamento caso o servico seja aprovado e autorizado pelo cliente.
   - Explique isso de forma transparente, ex.: "Como o produto esta fora da garantia, ha uma taxa de deslocamento e diagnostico que o tecnico cobra na visita. Mas fique tranquilo: se voce aprovar o orcamento e autorizar o servico, esse valor e abatido do total do conserto."
   - Se for dentro da garantia (marca autorizada), nao cite essa taxa.

7. Responda em markdown quando fizer sentido (listas, negrito), mas seja sucinta (3-6 linhas de media).
8. Se perguntarem sobre assuntos fora do escopo (politica, entretenimento, codigo, etc), redirecione gentilmente: "Posso te ajudar com assuntos da Mastermaq - solicitacao de atendimento, marcas, horarios ou duvidas sobre nossos servicos."
9. Use emojis com parcimonia (no maximo 1 por resposta) e apenas quando realmente agregarem.

NUNCA:
- Nunca invente precos, prazos exatos ou garanta resultado de conserto.
- Nunca forneca passo-a-passo tecnico para o cliente consertar sozinho.
- Nunca cite concorrentes.
- Nunca prometa horario/data de visita: a Central de Atendimento e quem confirma.
"""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    image: Optional[str] = None  # base64 data URL (data:image/...;base64,...) for user messages with attached image


class ChatStreamRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: Optional[str] = None  # server-side session id for logged-in persistence


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatFeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    message_idx: Optional[int] = None  # position in conversation
    rating: str  # "up" | "down"
    user_text: Optional[str] = ""
    assistant_text: str = ""
    comment: Optional[str] = ""


async def _get_user_optional(request: Request):
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def _get_llm_api_key():
    return os.environ.get("EMERGENT_LLM_KEY", "")


def _get_proxy_base():
    # matches emergentintegrations logic
    base = os.environ.get("integration_proxy_url") or os.environ.get("INTEGRATION_PROXY_URL") or "https://integrations.emergentagent.com"
    return base.rstrip("/") + "/llm"


@api_router.post("/chat/sessions")
async def create_chat_session(payload: ChatSessionCreate, request: Request):
    user = await _get_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login necessario para persistir sessoes")
    doc = {
        "user_id": user["_id"],
        "title": (payload.title or "Nova conversa")[:120],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.chat_sessions.insert_one(doc)
    return {"id": str(res.inserted_id), "title": doc["title"], "created_at": doc["created_at"], "updated_at": doc["updated_at"]}


@api_router.get("/chat/sessions")
async def list_chat_sessions(request: Request):
    user = await _get_user_optional(request)
    if not user:
        return []
    cursor = db.chat_sessions.find({"user_id": user["_id"]}).sort("updated_at", -1).limit(50)
    out = []
    async for s in cursor:
        out.append({
            "id": str(s["_id"]),
            "title": s.get("title", "Conversa"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
        })
    return out


@api_router.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: str, request: Request):
    user = await _get_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login necessario")
    try:
        sess = await db.chat_sessions.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    except Exception:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    if not sess:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    msgs_cursor = db.chat_messages.find({"session_id": session_id}).sort("created_at", 1)
    messages = []
    async for m in msgs_cursor:
        item = {"id": str(m["_id"]), "role": m["role"], "content": m["content"], "created_at": m.get("created_at")}
        if m.get("image"):
            item["image"] = m["image"]
        messages.append(item)
    return {"id": session_id, "title": sess.get("title"), "messages": messages}


@api_router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str, request: Request):
    user = await _get_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login necessario")
    try:
        res = await db.chat_sessions.delete_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    except Exception:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    await db.chat_messages.delete_many({"session_id": session_id})
    return {"deleted": res.deleted_count}


@api_router.post("/chat/stream")
async def chat_stream(payload: ChatStreamRequest, request: Request):
    user = await _get_user_optional(request)
    api_key = _get_llm_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key nao configurada")

    # Build messages with system prompt at start
    msgs = [{"role": "system", "content": MI_SYSTEM_PROMPT}]
    for m in payload.messages[-30:]:  # cap history
        if m.role not in ("user", "assistant"):
            continue
        if m.role == "user" and m.image:
            # Multimodal content for GPT-5.2 vision
            parts = []
            if m.content:
                parts.append({"type": "text", "text": m.content})
            parts.append({"type": "image_url", "image_url": {"url": m.image}})
            msgs.append({"role": "user", "content": parts})
        else:
            msgs.append({"role": m.role, "content": m.content})

    last_user = ""
    for m in reversed(payload.messages):
        if m.role == "user":
            last_user = m.content
            break

    # Persist user message immediately if logged-in session
    saved_session_id = None
    last_user_image = None
    for m in reversed(payload.messages):
        if m.role == "user":
            last_user_image = m.image
            break
    if user and payload.session_id:
        try:
            sess = await db.chat_sessions.find_one({"_id": ObjectId(payload.session_id), "user_id": user["_id"]})
            if sess:
                saved_session_id = payload.session_id
                user_doc = {
                    "session_id": saved_session_id,
                    "role": "user",
                    "content": last_user,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                if last_user_image:
                    user_doc["image"] = last_user_image
                await db.chat_messages.insert_one(user_doc)
                # if first user message and no real title, use first 60 chars
                if (sess.get("title") or "Nova conversa") == "Nova conversa" and last_user:
                    await db.chat_sessions.update_one({"_id": sess["_id"]}, {"$set": {"title": last_user[:60], "updated_at": datetime.now(timezone.utc).isoformat()}})
        except Exception as e:
            logger.warning(f"chat persist user err: {e}")

    async def event_gen():
        full_text = ""
        try:
            stream = litellm.completion(
                model="gpt-5.2",
                messages=msgs,
                api_key=api_key,
                api_base=_get_proxy_base(),
                custom_llm_provider="openai",
                stream=True,
                max_tokens=400,
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
                except Exception:
                    delta = None
                if delta:
                    full_text += delta
                    yield f"data: {_json.dumps({'type': 'delta', 'content': delta})}\n\n"
            # persist assistant response
            if saved_session_id and full_text:
                try:
                    await db.chat_messages.insert_one({
                        "session_id": saved_session_id,
                        "role": "assistant",
                        "content": full_text,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    await db.chat_sessions.update_one({"_id": ObjectId(saved_session_id)}, {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
                except Exception as e:
                    logger.warning(f"chat persist assistant err: {e}")

            # Detect schedule intent and emit a suggest_schedule event
            try:
                text_lower = (full_text + " " + last_user).lower()
                intent_keywords = [
                    "ordem de servi", "visita técnica", "visita tecnica",
                    "agendar visita", "abrir uma os", "abrir os",
                ]
                # Problem/defect keywords - also trigger pre-OS proactively (user described a problem)
                problem_keywords = [
                    "não liga", "nao liga", "não funciona", "nao funciona",
                    "não gela", "nao gela", "não esquenta", "nao esquenta",
                    "não esta ", "nao esta ", "não está ", "quebrou", "quebrada", "quebrado",
                    "parou", "travou", "vazando", "vaza", "vazamento", "ruido", "ruído", "barulho",
                    "faisca", "faísca", "mau cheiro", "cheiro ruim", "mancha",
                    "defeito", "estragou", "estragada", "estragado",
                    "não está gelando", "nao esta gelando",
                    "não seca", "nao seca", "não centrifuga", "nao centrifuga",
                    "não resfria", "nao resfria", "pingando", "sem ar",
                ]
                blob = text_lower
                has_intent = any(k in blob for k in intent_keywords)
                has_problem = any(k in blob for k in problem_keywords)
                if has_intent or has_problem:
                    # Try to extract equipment + brand from last user message
                    EQ_MAP = {
                        "geladeira": "geladeiras",
                        "freezer": "freezers",
                        "lavadora": "lavadoras",
                        "lava e seca": "lava-e-seca",
                        "coifa": "coifas",
                        "ar condicionado split": "ar-condicionado-split",
                        "ar-condicionado split": "ar-condicionado-split",
                        "split": "ar-condicionado-split",
                        "ar portátil": "ar-condicionado-portatil",
                        "ar portatil": "ar-condicionado-portatil",
                        "vrf": "vrf-hisense",
                        "triturador": "trituradores",
                    }
                    BRANDS_LOWER = [b.lower() for b in BRANDS]
                    eq_id = None
                    for k, v in EQ_MAP.items():
                        if k in text_lower:
                            eq_id = v
                            break
                    # scan recent user messages too
                    recent_user_blob = " ".join([m.content for m in payload.messages if m.role == "user"][-3:]).lower()
                    brand = ""
                    for b in BRANDS_LOWER:
                        if b in recent_user_blob or b in text_lower:
                            brand = next(x for x in BRANDS if x.lower() == b)
                            break
                    # Extract hints for defect description and model from recent user turns
                    defect_hint = ""
                    for m in reversed(payload.messages):
                        if m.role == "user" and m.content:
                            defect_hint = m.content[:240]
                            break
                    yield f"data: {_json.dumps({'type': 'suggest_schedule', 'equipment': eq_id or '', 'brand': brand, 'defect_hint': defect_hint, 'proactive': bool(has_problem and not has_intent)})}\n\n"
            except Exception as e:
                logger.warning(f"intent detect err: {e}")

            yield f"data: {_json.dumps({'type': 'done', 'content': full_text})}\n\n"
        except Exception as e:
            logger.error(f"chat stream err: {e}")
            yield f"data: {_json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


# ── STT (Whisper-1) ──────────────────────────────────────────────────
from fastapi import UploadFile, File
import io

@api_router.post("/chat/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe an audio file to text using Whisper-1 via Emergent key."""
    api_key = _get_llm_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key nao configurada")

    data = await audio.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio muito grande (limite 10MB)")

    # Build a BytesIO that has a .name attribute so OpenAI/Whisper can infer format
    filename = audio.filename or "audio.webm"
    bio = io.BytesIO(data)
    bio.name = filename

    try:
        from emergentintegrations.llm.openai import OpenAISpeechToText
        stt = OpenAISpeechToText(api_key=api_key)
        resp = await stt.transcribe(
            file=bio,
            model="whisper-1",
            response_format="json",
            language="pt",
            temperature=0.0,
        )
        text = getattr(resp, "text", None) or (resp.get("text") if isinstance(resp, dict) else None) or ""
        return {"text": text.strip()}
    except Exception as e:
        logger.error(f"stt err: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na transcricao: {str(e)[:200]}")


# ── Image upload (returns base64 data URL to attach in chat) ─────────
@api_router.post("/chat/upload")
async def chat_upload_image(image: UploadFile = File(...)):
    """Accept an image and return a data URL (base64) usable by chat stream as multimodal input."""
    content_type = (image.content_type or "").lower()
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail="Formato nao suportado. Use JPG, PNG, WEBP ou GIF.")
    data = await image.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Imagem muito grande (limite 5MB).")
    import base64 as _b64
    b64 = _b64.b64encode(data).decode("ascii")
    return {
        "data_url": f"data:{content_type};base64,{b64}",
        "size": len(data),
        "content_type": content_type,
    }


# ── Feedback 👍👎 ────────────────────────────────────────────────────
# ── Webhook: updates de status vindos do sistema externo (Mastermaq Systems) ─
class ExternalStatusUpdate(BaseModel):
    os_number: Optional[str] = None        # internal OS (preferred)
    external_os_number: Optional[str] = None  # ext OS (EXT-...)
    status: str
    technician: Optional[str] = None
    scheduled_for: Optional[str] = None
    notes: Optional[str] = None
    event_type: Optional[str] = "status_update"


@api_router.post("/external/webhook/status")
async def external_status_webhook(body: ExternalStatusUpdate, request: Request):
    """
    Receives OS status updates from the external system.
    Auth: X-API-Key header equal to EXTERNAL_OS_API_KEY env var.
    Matches OS by os_number (internal) first, then external_os_number.
    """
    key = os.environ.get("EXTERNAL_OS_API_KEY", "")
    recv = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if not key or recv != key:
        raise HTTPException(status_code=401, detail="API key invalida")

    # Build a lookup query that is robust to the external system sending the
    # external OS number under the `os_number` key (common case: external API
    # uses its own numeric id like "27677" which corresponds to our
    # `external_os_number`, while our internal id has the "OS-..." prefix).
    candidates = []
    if body.os_number:
        candidates.append({"os_number": body.os_number})
        candidates.append({"external_os_number": body.os_number})
    if body.external_os_number:
        candidates.append({"external_os_number": body.external_os_number})
        candidates.append({"os_number": body.external_os_number})
    if not candidates:
        raise HTTPException(status_code=400, detail="os_number ou external_os_number e obrigatorio")
    query = candidates[0] if len(candidates) == 1 else {"$or": candidates}

    update = {
        "status": body.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.technician:   update["technician"] = body.technician
    if body.scheduled_for: update["scheduled_for"] = body.scheduled_for
    if body.notes:        update["notes_ext"] = body.notes

    res = await db.service_orders.update_one(query, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="OS nao encontrada")

    # Log event for audit + polling. Use the matched OS number explicitly so
    # the event row always carries `os_number` (the external system may have
    # sent only `external_os_number`).
    matched_doc = await db.service_orders.find_one(query, {"os_number": 1, "external_os_number": 1, "_id": 0})
    event_doc = {
        "os_number": (matched_doc or {}).get("os_number"),
        "external_os_number": (matched_doc or {}).get("external_os_number"),
        "event_type": body.event_type or "status_update",
        "status": body.status,
        "technician": body.technician,
        "scheduled_for": body.scheduled_for,
        "notes": body.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.service_order_events.insert_one(event_doc)
    logger.info(f"[webhook-status] OS={(matched_doc or {}).get('os_number')} status={body.status} ev={body.event_type}")
    return {"ok": True, "matched": res.matched_count, "modified": res.modified_count}


@api_router.get("/service-orders/{os_number}/events")
async def os_events(os_number: str, request: Request):
    """Polling fallback: retorna eventos da OS (requer login do dono ou admin)."""
    user = await get_current_user(request)
    o = await db.service_orders.find_one({"os_number": os_number})
    if not o:
        raise HTTPException(status_code=404, detail="OS nao encontrada")
    if o.get("user_id") != user.get("_id") and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Sem permissao")
    cursor = db.service_order_events.find({"os_number": os_number}).sort("created_at", -1).limit(50)
    out = []
    async for ev in cursor:
        out.append({
            "event_type": ev.get("event_type"),
            "status": ev.get("status"),
            "technician": ev.get("technician"),
            "scheduled_for": ev.get("scheduled_for"),
            "notes": ev.get("notes"),
            "created_at": ev.get("created_at"),
        })
    return {"os_number": os_number, "current_status": o.get("status"), "events": out}



async def chat_feedback(body: ChatFeedbackRequest, request: Request):
    if body.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating deve ser 'up' ou 'down'")
    user = await _get_user_optional(request)
    doc = {
        "user_id": user["_id"] if user else None,
        "session_id": body.session_id,
        "message_idx": body.message_idx,
        "rating": body.rating,
        "user_text": (body.user_text or "")[:2000],
        "assistant_text": (body.assistant_text or "")[:4000],
        "comment": (body.comment or "")[:500],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.chat_feedback.insert_one(doc)
    return {"ok": True}


# ── TTS (Text-to-Speech) ─────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "nova"  # cleaner pt-BR pronunciation
    speed: Optional[float] = 1.0


def _sanitize_tts_text(raw: str) -> str:
    """Remove markdown, emojis and other artifacts so the TTS engine does not
    read literal '*', '_', '#', bullets, or emoji-like tokens (which cause
    robotic pauses and odd pronunciation)."""
    import re as _re
    t = raw or ""
    # strip fenced code blocks
    t = _re.sub(r"```[\s\S]*?```", " ", t)
    # inline code `foo`
    t = _re.sub(r"`([^`]+)`", r"\1", t)
    # markdown links [text](url) -> text
    t = _re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # bold/italic/underline markers
    t = _re.sub(r"[*_~]+", " ", t)
    # headings / blockquotes markers at line start
    t = _re.sub(r"(^|\n)\s*[#>]+\s*", r"\1", t)
    # bullet markers
    t = _re.sub(r"(^|\n)\s*[-•]\s+", r"\1", t)
    # strip most emojis / pictographs
    try:
        t = _re.sub(
            r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]",
            "",
            t,
        )
    except Exception:
        pass
    # collapse whitespace
    t = _re.sub(r"[ \t]+", " ", t)
    t = _re.sub(r"\n{3,}", "\n\n", t)
    # ensure sentence ends for prosody if missing
    t = t.strip()
    if t and t[-1] not in ".!?…":
        t += "."
    return t


@api_router.post("/chat/tts")
async def chat_tts(body: TTSRequest):
    """Return mp3 audio for the given text using OpenAI tts-1-hd via Emergent key."""
    api_key = _get_llm_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key nao configurada")
    text = _sanitize_tts_text((body.text or "").strip())
    if not text:
        raise HTTPException(status_code=400, detail="text vazio")
    # Cap for single TTS call
    if len(text) > 4000:
        text = text[:4000]
    try:
        from emergentintegrations.llm.openai import OpenAITextToSpeech
        tts = OpenAITextToSpeech(api_key=api_key)
        # tts-1-hd gives much more natural prosody in pt-BR; nova is the
        # voice with cleanest Portuguese pronunciation (coral has US accent).
        audio_bytes = await tts.generate_speech(
            text=text,
            model="tts-1-hd",
            voice=body.voice or "nova",
            speed=max(0.5, min(2.0, body.speed or 1.0)),
            response_format="mp3",
        )
        from fastapi.responses import Response as FastResponse
        return FastResponse(content=audio_bytes, media_type="audio/mpeg", headers={
            "Cache-Control": "no-store",
        })
    except Exception as e:
        logger.error(f"tts err: {e}")
        raise HTTPException(status_code=500, detail=f"Falha TTS: {str(e)[:200]}")


# ── Startup ──────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.service_orders.create_index("os_number", unique=True)
    await db.service_orders.create_index("user_id")
    await db.blog_articles.create_index("slug", unique=True)

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@mastermaq.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "mastermaq@2026")
    admin_phone = os.environ.get("ADMIN_PHONE", "31999999999")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Admin Mastermaq",
            "phone": admin_phone,
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin created: {admin_email}")
    else:
        # Ensure admin has a valid phone (required for external OS sync).
        updates = {}
        if not existing.get("phone"):
            updates["phone"] = admin_phone
        if not verify_password(admin_password, existing["password_hash"]):
            updates["password_hash"] = hash_password(admin_password)
        if updates:
            await db.users.update_one({"email": admin_email}, {"$set": updates})
            logger.info(f"Admin updated: {list(updates.keys())}")

    # Seed blog articles
    count = await db.blog_articles.count_documents({})
    if count == 0:
        articles = [
            {
                "title": "Como Manter Sua Geladeira Funcionando Perfeitamente",
                "slug": "manter-geladeira-funcionando",
                "content": "A manutencao preventiva da sua geladeira e essencial para garantir seu funcionamento ideal e prolongar sua vida util.\n\n**1. Limpe as bobinas do condensador**\nAs bobinas acumulam poeira ao longo do tempo, forcando o motor a trabalhar mais. Limpe-as a cada 6 meses.\n\n**2. Verifique as borrachas de vedacao**\nBorrachas danificadas permitem a entrada de ar quente, aumentando o consumo de energia.\n\n**3. Mantenha a temperatura ideal**\nA temperatura recomendada e entre 3C e 5C para o refrigerador e -18C para o freezer.\n\n**4. Nao sobrecarregue**\nColocar muitos itens dificulta a circulacao de ar frio.\n\n**5. Faca manutencao periodica**\nAgende uma revisao anual com tecnicos especializados da Mastermaq.",
                "summary": "Dicas essenciais para manter sua geladeira funcionando com eficiencia e prolongar sua vida util.",
                "category": "Manutencao",
                "author": "Equipe Mastermaq",
                "published": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "title": "Quando Trocar o Filtro do Ar Condicionado Split",
                "slug": "trocar-filtro-ar-condicionado",
                "content": "O filtro do ar condicionado split e um componente crucial para a qualidade do ar e eficiencia do equipamento.\n\n**Por que trocar o filtro?**\nFiltros sujos reduzem a eficiencia do ar condicionado em ate 15%, aumentam o consumo de energia e podem causar problemas respiratorios.\n\n**Quando trocar?**\n- A cada 3 meses em ambientes residenciais\n- Mensalmente em ambientes com pets ou fumantes\n- Sempre que notar acumulo visivel de poeira\n\n**Sinais de que o filtro precisa ser trocado:**\n- Ar condicionado demora mais para resfriar o ambiente\n- Ruido excessivo durante o funcionamento\n- Cheiro desagradavel ao ligar\n- Aumento na conta de energia\n\nNa Mastermaq, realizamos a troca e higienizacao completa do seu ar condicionado.",
                "summary": "Saiba o momento certo de trocar o filtro do seu ar condicionado split.",
                "category": "Ar Condicionado",
                "author": "Equipe Mastermaq",
                "published": True,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                "updated_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            },
            {
                "title": "5 Sinais de Que Sua Lava e Seca Precisa de Manutencao",
                "slug": "sinais-lava-seca-manutencao",
                "content": "Sua lava e seca e um dos equipamentos mais utilizados. Fique atento a estes sinais:\n\n**1. Ruidos estranhos durante o ciclo**\nBatidas, rangidos ou zumbidos podem indicar problemas nos rolamentos.\n\n**2. Roupas nao ficam secas**\nSe as roupas saem umidas apos o ciclo de secagem, pode haver problemas na resistencia.\n\n**3. Vazamentos de agua**\nMangueiras danificadas ou bomba com defeito sao causas comuns.\n\n**4. Cheiro de mofo ou queimado**\nMofo indica acumulo de umidade, enquanto cheiro de queimado pode ser sinal de problema eletrico.\n\n**5. Erro no painel**\nCodigos de erro sao alertas do sistema. Consulte o manual ou entre em contato com a Mastermaq.\n\nNao ignore esses sinais! Agende uma visita tecnica.",
                "summary": "Identifique os sinais de que sua lava e seca precisa de atencao tecnica.",
                "category": "Lava e Seca",
                "author": "Equipe Mastermaq",
                "published": True,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
                "updated_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            },
        ]
        await db.blog_articles.insert_many(articles)
        logger.info("Blog articles seeded")

    # Write test credentials (only in development)
    try:
        os.makedirs("/app/memory", exist_ok=True)
        with open("/app/memory/test_credentials.md", "w") as f:
            f.write(f"# Test Credentials\n\n## Admin\n- Email: {admin_email}\n- Password: {admin_password}\n- Role: admin\n\n## Auth Endpoints\n- POST /api/auth/register\n- POST /api/auth/login\n- POST /api/auth/logout\n- GET /api/auth/me\n- POST /api/auth/refresh\n- PUT /api/auth/profile\n")
    except Exception:
        pass

# ---------------- Rate limiting (in-memory sliding window per IP) ----------------
import time as _rl_time
from collections import defaultdict as _rl_defaultdict, deque as _rl_deque
from fastapi.responses import JSONResponse as _RLJSONResponse

_RL_BUCKETS = _rl_defaultdict(_rl_deque)  # key -> deque[timestamps]

# (max_requests, window_seconds) por categoria
_RL_RULES = {
    "auth": (15, 60),      # login / register / google
    "chat": (90, 60),      # Mi chat / voice (SSE + polling)
    "write": (60, 60),     # POST/PUT/PATCH/DELETE
    "default": (200, 60),  # GET geral
}


def _rl_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rl_category(request: Request) -> str:
    path = request.url.path
    if path.startswith(("/api/auth/login", "/api/auth/register", "/api/auth/google")):
        return "auth"
    if path.startswith("/api/chat"):
        return "chat"
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    return "default"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    # Só limita rotas /api; ignora preflight e o webhook externo (auth própria via X-API-Key)
    if (
        not path.startswith("/api")
        or request.method == "OPTIONS"
        or path.startswith("/api/external/webhook")
    ):
        return await call_next(request)

    cat = _rl_category(request)
    max_req, window = _RL_RULES[cat]
    ip = _rl_client_ip(request)
    key = f"{cat}:{ip}"
    now = _rl_time.time()
    bucket = _RL_BUCKETS[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= max_req:
        retry_after = int(window - (now - bucket[0])) + 1
        return _RLJSONResponse(
            status_code=429,
            content={"detail": "Muitas requisições. Aguarde alguns instantes e tente novamente."},
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)
    return await call_next(request)


app.include_router(api_router)

cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
origins_list = [o.strip() for o in cors_origins.split(",") if o.strip()]
if "*" in origins_list:
    origins_list = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=True if "*" not in origins_list else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown():
    client.close()
