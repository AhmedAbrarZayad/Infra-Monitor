from ml_model.presenters import present_anomaly


FEATURE_LABELS = {
    "cpu_r": ("CPU", "%"),
    "mem_u": ("Memory", "%"),
    "disk_r": ("Disk read", "B/s"),
    "disk_w": ("Disk write", "B/s"),
    "eth1_fi": ("Network in", "B/s"),
    "eth1_fo": ("Network out", "B/s"),
}


def present_assistant_anomaly(anomaly):
    data = present_anomaly(anomaly)
    service = anomaly.service_id
    data["lifecycle"] = {
        "status": service.status if service else "UNKNOWN",
        "reason": service.lifecycle_reason if service else "service_unavailable",
        "last_reported_at": service.last_reported_at if service else None,
    }
    data["evidence"] = [
        {
            "key": key,
            "label": label,
            "value": anomaly.feature_values.get(key),
            "unit": unit,
        }
        for key, (label, unit) in FEATURE_LABELS.items()
    ]
    return data


def present_conversation(conversation):
    return {
        "id": str(conversation.conversation_id),
        "anomaly_id": str(conversation.anomaly_id or ""),
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


def present_message(message):
    return {
        "id": str(message.message_id),
        "sender": message.sender_type.lower(),
        "text": message.message,
        "evidence": message.evidence,
        "client_message_id": str(message.client_message_id or ""),
        "created_at": message.created_at.isoformat(),
    }
