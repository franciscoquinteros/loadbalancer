#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pydantic import BaseModel
from typing import Optional


class UserCreationRequest(BaseModel):
    """Request model for user creation API"""
    conversation_id: str
    captured_user_name: str
    candidate_username: str
    attempt_number: int


class UserCreationResponse(BaseModel):
    """Response model for user creation API"""
    status: str  # "success", "conflict", "error"
    generated_username: Optional[str] = None
    response_message: str
    error_detail: Optional[str] = None


class BalanceLoadRequest(BaseModel):
    """Request model for balance loading API (without bonus)"""
    conversation_id: str
    username: str
    amount: int


class BalanceLoadBonusRequest(BaseModel):
    """Request model for balance loading API (with bonus)"""
    conversation_id: str
    username: str
    amount: int
    bonus_percentage: int


class BalanceLoadResponse(BaseModel):
    """Response model for balance loading API"""
    status: str  # "success", "error"
    username: Optional[str] = None
    amount_loaded: Optional[int] = None
    bonus_amount: Optional[int] = None
    response_message: str
    error_detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    service: str
    timestamp: str