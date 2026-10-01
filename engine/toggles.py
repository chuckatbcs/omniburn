#!/usr/bin/env python3
"""
Model and Provider toggle management module for OmniBurn.
Allows enabling/disabling individual models or entire providers/subscriptions,
logging state changes to model_changelog, and refactoring recommendations dynamically.
"""

from datetime import datetime, timezone
from engine.db import get_connection

def toggle_model(model_id, is_active=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT model_id, display_name, is_active FROM models WHERE model_id = ?", (model_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"error": f"Model '{model_id}' not found"}

    current_state = bool(row["is_active"])
    new_state = (not current_state) if is_active is None else bool(is_active)
    new_val = 1 if new_state else 0
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("UPDATE models SET is_active = ? WHERE model_id = ?", (new_val, model_id))

    event_type = "MODEL_ENABLED" if new_state else "MODEL_DISABLED"
    details = f"Model '{row['display_name']}' ({model_id}) set to {'ACTIVE' if new_state else 'DISABLED'}."
    cursor.execute("""
        INSERT INTO model_changelog (timestamp, event_type, model_id, details)
        VALUES (?, ?, ?, ?)
    """, (now_iso, event_type, model_id, details))

    conn.commit()
    conn.close()
    return {
        "status": "ok",
        "model_id": model_id,
        "display_name": row["display_name"],
        "is_active": new_state,
        "event_type": event_type
    }

def toggle_provider(provider_or_sub_id, is_active=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Check if matches subscription ID or provider name
    cursor.execute("""
        SELECT id, name, provider, status FROM subscriptions
        WHERE id = ? OR provider LIKE ?
    """, (provider_or_sub_id, f"%{provider_or_sub_id}%"))
    subs = cursor.fetchall()

    if not subs:
        conn.close()
        return {"error": f"Provider/Subscription '{provider_or_sub_id}' not found"}

    target_sub = subs[0]
    current_status = target_sub["status"]
    if is_active is None:
        new_active = (current_status != "active")
    else:
        new_active = bool(is_active)

    new_status = "active" if new_active else "disabled"
    new_model_val = 1 if new_active else 0

    # Update subscription status
    cursor.execute("UPDATE subscriptions SET status = ? WHERE id = ?", (new_status, target_sub["id"]))

    # Update models associated with this subscription's pools
    cursor.execute("""
        UPDATE models
        SET is_active = ?
        WHERE pool_id IN (SELECT id FROM quota_pools WHERE sub_id = ?)
    """, (new_model_val, target_sub["id"]))
    models_affected = cursor.rowcount

    event_type = "PROVIDER_ENABLED" if new_active else "PROVIDER_DISABLED"
    details = f"Subscription/Provider '{target_sub['name']}' set to {new_status.upper()} ({models_affected} models updated)."
    cursor.execute("""
        INSERT INTO model_changelog (timestamp, event_type, model_id, details)
        VALUES (?, ?, ?, ?)
    """, (now_iso, event_type, target_sub["id"], details))

    conn.commit()
    conn.close()
    return {
        "status": "ok",
        "sub_id": target_sub["id"],
        "name": target_sub["name"],
        "provider": target_sub["provider"],
        "is_active": new_active,
        "status_text": new_status,
        "models_affected": models_affected,
        "event_type": event_type
    }

if __name__ == "__main__":
    import sys
    print("Testing toggles...")
    res = toggle_model("gemini-3.8-flash-medium", is_active=False)
    print("Disable Flash:", res)
    res2 = toggle_model("gemini-3.8-flash-medium", is_active=True)
    print("Re-enable Flash:", res2)
