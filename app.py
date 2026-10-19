from typing import Optional
from fastapi import FastAPI, Request, status, Response, Body, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

# מילון בזיכרון לשמירת המשלוחים והמונה ל-ID
deliveries_db = {}
next_id = 1

VALID_STATUSES = ["created", "in_transit", "delivered"]


# טיפול בשגיאות HTTP
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )


# טיפול בשגיאות ולידציה
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid request body"}
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# יצירת משלוח חדש
@app.post("/deliveries", status_code=201)
def create_delivery(payload: dict = Body(...)):
    global next_id
    
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid payload format"})

    recipient = payload.get("recipient")
    address = payload.get("address")
    
    if not isinstance(recipient, str) or not recipient.strip():
        return JSONResponse(status_code=400, content={"error": "Invalid recipient"})
    if not isinstance(address, str) or not address.strip():
        return JSONResponse(status_code=400, content={"error": "Invalid address"})
    
    delivery = {
        "id": next_id,
        "recipient": recipient,
        "address": address,
        "status": "created"
    }
    
    deliveries_db[next_id] = delivery
    next_id += 1
    
    return delivery


# קבלת רשימת משלוחים עם אפשרות לסינון
@app.get("/deliveries")
def get_deliveries(status: Optional[str] = None):
    if status is not None:
        if status not in VALID_STATUSES:
            return JSONResponse(status_code=400, content={"error": "Invalid status filter"})
        filtered = [d for d in deliveries_db.values() if d["status"] == status]
        return filtered
    return list(deliveries_db.values())


# קבלת משלוח לפי ID
@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    return deliveries_db[delivery_id]


# עדכון סטטוס משלוח
@app.patch("/deliveries/{delivery_id}/status")
def update_delivery_status(delivery_id: int, payload: dict = Body(...)):
    if delivery_id not in deliveries_db:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    
    if not isinstance(payload, dict) or "status" not in payload:
        return JSONResponse(status_code=400, content={"error": "Invalid status payload"})
    
    new_status = payload["status"]
    if new_status not in VALID_STATUSES:
        return JSONResponse(status_code=400, content={"error": "Invalid status value"})
    
    current_status = deliveries_db[delivery_id]["status"]
    
    # בדיקת מעבר מעבר סטטוס חוקי בלבד: created -> in_transit -> delivered
    allowed_transitions = {
        "created": "in_transit",
        "in_transit": "delivered"
    }
    
    if allowed_transitions.get(current_status) != new_status:
        return JSONResponse(status_code=409, content={"error": "Invalid status transition"})
    
    deliveries_db[delivery_id]["status"] = new_status
    return deliveries_db[delivery_id]


# מחיקת משלוח
@app.delete("/deliveries/{delivery_id}")
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    
    if deliveries_db[delivery_id]["status"] != "created":
        return JSONResponse(status_code=409, content={"error": "Cannot delete non-created delivery"})
    
    del deliveries_db[delivery_id]
    return Response(status_code=204)