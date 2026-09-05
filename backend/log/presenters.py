def present_log(entry):
    return {
        "id": entry.log_id,
        "server_id": entry.server_id_id,
        "service_id": entry.service_id_id,
        "source": entry.source,
        "level": entry.log_level,
        "message": entry.message,
        "metadata": entry.metadata,
        "logged_at": entry.logged_at,
        "ingested_at": entry.ingested_at,
    }
