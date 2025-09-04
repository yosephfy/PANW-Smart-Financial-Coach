from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from .. import db as db_mod
from ..utils.auth import current_username
from ..services import goals_service as svc


router = APIRouter(tags=["goals"])


class GoalCreateRequest(BaseModel):
    user_id: Optional[str] = None
    name: str
    target_amount: float
    target_date: str


@router.post("/goals")
def goal_create(body: GoalCreateRequest, request: Request):
    uid = body.user_id or current_username(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_authenticated")
    with db_mod.get_connection() as conn:
        try:
            return svc.create(conn, uid, body.name, body.target_amount, body.target_date)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/goals")
def goals_list(user_id: str):
    with db_mod.get_connection() as conn:
        return svc.list_for_user(conn, user_id)


@router.get("/users/me/goals")
def goals_list_me(request: Request):
    u = current_username(request)
    if not u:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return goals_list(u)


@router.get("/goals/{goal_id}/evaluate")
def goal_evaluate(goal_id: str):
    with db_mod.get_connection() as conn:
        try:
            return svc.evaluate(conn, goal_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


class GoalUpdateRequest(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[str] = None
    status: Optional[str] = None


@router.patch("/goals/{goal_id}")
def goal_update(goal_id: str, body: GoalUpdateRequest):
    with db_mod.get_connection() as conn:
        try:
            return svc.update(conn, goal_id, name=body.name, target_amount=body.target_amount, target_date=body.target_date, status=body.status)
        except KeyError:
            raise HTTPException(status_code=404, detail="goal_not_found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

