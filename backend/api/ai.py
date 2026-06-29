import uuid
from datetime import datetime
from typing import Any

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.models.models import AIConversation
from backend.models.schemas import AIConversation as ConversationSchema
from backend.services.ai_service import AIService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSchema])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Retrieve all AI support conversations for this user."""
    stmt = (
        select(AIConversation)
        .where(
            AIConversation.org_id == uuid.UUID(current_user.org_id),
            AIConversation.user_id == uuid.UUID(current_user.id),
        )
        .order_by(AIConversation.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/conversations", response_model=ConversationSchema)
async def chat(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Send a message to an AI assistant and get a response.

    Request format:
    {
      "conversation_id": "optional-uuid-string",
      "message": "Hello, how do I calculate transportation footprint?"
    }
    """
    user_msg_content = payload.get("message")
    conv_id_str = payload.get("conversation_id")

    if not user_msg_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is required",
        )

    # Input validation: cap message length
    if len(user_msg_content) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message too long (max 4000 characters)",
        )

    # 1. Fetch or create conversation
    conv = None
    if conv_id_str:
        try:
            conv_id = uuid.UUID(conv_id_str)
            stmt = select(AIConversation).where(
                AIConversation.id == conv_id,
                AIConversation.org_id == uuid.UUID(current_user.org_id),
            )
            res = await db.execute(stmt)
            conv = res.scalars().first()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format",
            )

    if not conv:
        conv = AIConversation(
            org_id=uuid.UUID(current_user.org_id),
            user_id=uuid.UUID(current_user.id),
            messages=[],
        )
        db.add(conv)
        await db.flush()

    # 2. Append User Message
    current_messages = list(conv.messages or [])
    user_msg = {
        "role": "user",
        "content": user_msg_content,
        "timestamp": datetime.now().isoformat(),
    }
    current_messages.append(user_msg)

    # 3. Request completion from LLM API
    ai_response_content = await AIService.generate_response(current_messages)

    # 4. Append AI Message
    ai_msg = {
        "role": "assistant",
        "content": ai_response_content,
        "timestamp": datetime.now().isoformat(),
    }
    current_messages.append(ai_msg)

    # 5. Save and return updated conversation
    # We must explicitly set flag for mutation detection on JSONB columns in SQLAlchemy
    conv.messages = current_messages
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return conv
