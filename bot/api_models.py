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


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    service: str
    timestamp: str