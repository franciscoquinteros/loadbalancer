#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api_models import UserCreationRequest, UserCreationResponse, HealthResponse
from browser_automation import create_user
from sheets_logger import log_user_creation

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RPA Balance Loader API",
    description="API wrapper for RPA bot to create users via browser automation",
    version="1.0.0"
)

# Add CORS middleware for external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for external access
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Optional API key from environment
API_KEY = os.getenv("RPA_BOT_API_KEY")


def verify_api_key(request_api_key: str = None) -> bool:
    """Verify API key if configured"""
    if not API_KEY:
        return True  # No API key required
    return request_api_key == API_KEY


@app.post("/api/create-user", response_model=UserCreationResponse)
async def create_user_endpoint(request: UserCreationRequest):
    """
    Create a new user via browser automation
    
    This endpoint wraps the browser_automation.create_user function
    and returns the result in the format expected by the Kommo bot.
    """
    try:
        logger.info(f"API request received: conversation_id={request.conversation_id}, "
                   f"username={request.candidate_username}, attempt={request.attempt_number}")
        
        # Call the existing browser automation function
        success, message = await create_user(request.candidate_username, "cocos")
        
        if success:
            # Log successful creation to Google Sheets
            try:
                await log_user_creation(
                    username=request.candidate_username,
                    operator=f"kommo_bot_{request.conversation_id}"
                )
                logger.info(f"User creation logged to Google Sheets: {request.candidate_username}")
            except Exception as e:
                logger.error(f"Failed to log user creation to Google Sheets: {e}")
                # Continue with success response even if logging fails
            
            response = UserCreationResponse(
                status="success",
                generated_username=request.candidate_username,
                response_message=f"Usuario {request.candidate_username} creado exitosamente. Contraseña: cocos"
            )
            logger.info(f"User creation successful: {request.candidate_username}")
            return response
        
        else:
            # Determine if this is a conflict (username exists) or system error
            message_lower = message.lower()
            
            if any(keyword in message_lower for keyword in ['exists', 'already exists', 'duplicate', 'taken']):
                # Username conflict
                response = UserCreationResponse(
                    status="conflict",
                    response_message="Username already exists",
                    error_detail=f"User {request.candidate_username} already exists in the system"
                )
                logger.warning(f"Username conflict: {request.candidate_username}")
                return response
            else:
                # System error
                response = UserCreationResponse(
                    status="error",
                    response_message="User creation failed",
                    error_detail=message
                )
                logger.error(f"User creation failed: {request.candidate_username} - {message}")
                return response
                
    except Exception as e:
        logger.error(f"API error creating user {request.candidate_username}: {str(e)}")
        response = UserCreationResponse(
            status="error",
            response_message="Internal server error",
            error_detail=f"Unexpected error: {str(e)}"
        )
        return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return HealthResponse(
        status="healthy",
        service="RPA Bot API",
        timestamp=datetime.now().isoformat()
    )


@app.get("/")
async def root():
    """
    Root endpoint with basic information
    """
    return {
        "service": "RPA Balance Loader API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "create_user": "/api/create-user",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8001
    port = int(os.getenv("RPA_API_PORT", 8001))
    host = os.getenv("RPA_API_HOST", "0.0.0.0")  # Listen on all interfaces for external access
    
    logger.info(f"Starting RPA API server on {host}:{port}")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Set to True for development
    )