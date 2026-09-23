from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.lmstudio_client import LMStudioClient
from app.llm.model_catalog import (
    list_chat_models,
    list_embedding_models,
)
from app.llm.provider_store import (
    delete_provider,
    get_active,
    load_settings,
    public_provider,
    set_active,
    upsert_provider,
)


router = APIRouter(
    prefix="/llm",
    tags=["llm"],
)


class ProviderPayload(BaseModel):

    id: str | None = None
    kind: str = "custom"
    label: str = "Custom API"
    base_url: str
    api_key: str = ""
    chat_model: str = ""
    embedding_model: str = ""


class ActivatePayload(BaseModel):

    provider_id: str
    chat_model: str | None = None
    embedding_model: str | None = None


@router.get("/settings")
def get_settings():

    data = load_settings()
    active = get_active()

    return {
        "active_id": data.get("active_id"),
        "active": public_provider(active),
        "providers": [
            public_provider(item)
            for item in data.get("providers") or []
        ],
    }


@router.post("/providers")
def save_provider(payload: ProviderPayload):

    try:
        record = upsert_provider(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return public_provider(record)


@router.delete("/providers/{provider_id}")
def remove_provider(provider_id: str):

    try:
        delete_provider(provider_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {"status": "deleted", "id": provider_id}


@router.post("/activate")
def activate_provider(payload: ActivatePayload):

    try:
        record = set_active(
            payload.provider_id,
            payload.chat_model,
            payload.embedding_model,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    from app.api.dependencies import application_dependencies
    from app.resume.resume_agent import ResumeAgent
    application_dependencies.resume_agent = ResumeAgent()
    application_dependencies._job_search_pipeline = None

    return {
        "status": "active",
        "active": public_provider(record),
    }


@router.get("/providers/{provider_id}/models")
def list_provider_models(provider_id: str):

    data = load_settings()
    record = None

    for item in data.get("providers") or []:
        if item.get("id") == provider_id:
            record = item
            break

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown LLM provider.",
        )

    client = LMStudioClient(
        base_url=record.get("base_url"),
        llm_model=record.get("chat_model"),
        embedding_model=record.get("embedding_model"),
        api_key=record.get("api_key") or "",
        kind=record.get("kind"),
    )

    try:
        models = list_chat_models(
            record.get("kind") or "",
            record.get("base_url") or "",
            client._headers(),
        )
        embedding_models = list_embedding_models(
            record.get("kind") or "",
            record.get("base_url") or "",
            client._headers(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not list models: {exc}",
        ) from exc

    return {
        "id": provider_id,
        "kind": record.get("kind"),
        "models": models,
        "embedding_models": embedding_models,
        "embedding_model": record.get("embedding_model") or "",
        "reachable": bool(models or embedding_models),
        "count": len(models),
    }
