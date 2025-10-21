#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import asyncio
import math
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .api_models import UserCreationRequest, UserCreationResponse, HealthResponse, BalanceLoadRequest, BalanceLoadBonusRequest, BalanceLoadResponse
from .browser_automation import create_user, assign_balance
from .sheets_logger import log_user_creation, log_chip_load

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

# Platform configuration
PLATFORM_URL = os.getenv("PLATFORM_URL", "https://yourplatform.com")
PLATFORM_NAME = os.getenv("PLATFORM_NAME", "YourPlatform")


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
        success, message = await create_user(request.candidate_username, "ganamos1")
        
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
            
            # Create the same copyable message format as the Telegram bot
            copyable_message = (
                f"Cuenta creada! 🙌\n"
                f"🔑Usuario: {request.candidate_username}\n"
                f"🔒Contraseña: ganamos1\n"
                f"Plataforma: https://ganamosnet.io\n"
                f"Te dejo el ALIAS aqui abajo para cuando quieras cargar\n\n"
            )
            
            response = UserCreationResponse(
                status="success",
                generated_username=request.candidate_username,
                response_message=copyable_message
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


@app.post("/api/load-balance", response_model=BalanceLoadResponse)
async def load_balance_endpoint(request: BalanceLoadRequest):
    """
    Load balance to a user (without bonus)
    
    This endpoint loads a specified amount to a user's account
    without any bonus additions.
    """
    try:
        logger.info(f"Balance load request received: conversation_id={request.conversation_id}, "
                   f"username={request.username}, amount={request.amount}")
        
        # Call the existing browser automation function
        success, message = await assign_balance(request.username, request.amount)
        
        if success:
            # Log successful balance load to Google Sheets
            try:
                await log_chip_load(
                    username=request.username,
                    operator=f"api_bot_{request.conversation_id}",
                    amount=request.amount,
                    bonus_percentage=None,
                    load_type="normal"
                )
                logger.info(f"Balance load logged to Google Sheets: {request.amount} to {request.username}")
            except Exception as e:
                logger.error(f"Failed to log balance load to Google Sheets: {e}")
                # Continue with success response even if logging fails
            
            response = BalanceLoadResponse(
                status="success",
                username=request.username,
                amount_loaded=request.amount,
                response_message=f"Successfully loaded {request.amount} pesos to {request.username}"
            )
            logger.info(f"Balance load successful: {request.amount} to {request.username}")
            return response
        
        else:
            # Balance loading failed
            response = BalanceLoadResponse(
                status="error",
                username=request.username,
                response_message="Balance loading failed",
                error_detail=message
            )
            logger.error(f"Balance load failed: {request.username} - {message}")
            return response
                
    except Exception as e:
        logger.error(f"API error loading balance to {request.username}: {str(e)}")
        response = BalanceLoadResponse(
            status="error",
            username=request.username,
            response_message="Internal server error",
            error_detail=f"Unexpected error: {str(e)}"
        )
        return response


@app.post("/api/load-balance-bonus", response_model=BalanceLoadResponse)
async def load_balance_bonus_endpoint(request: BalanceLoadBonusRequest):
    """
    Load balance to a user with bonus

    This endpoint loads a specified base amount plus a bonus percentage
    to a user's account using the bonus feature in the deposit form.
    """
    try:
        logger.info(f"Balance load with bonus request received: conversation_id={request.conversation_id}, "
                   f"username={request.username}, amount={request.amount}, bonus={request.bonus_percentage}%")

        # Validate bonus percentage range
        if request.bonus_percentage < 1 or request.bonus_percentage > 200:
            response = BalanceLoadResponse(
                status="error",
                username=request.username,
                response_message="Invalid bonus percentage",
                error_detail="Bonus percentage must be between 1 and 200"
            )
            return response

        # Single transaction with bonus activated
        success, message = await assign_balance(request.username, request.amount, request.bonus_percentage)

        if success:
            # Transaction successful - log to Google Sheets
            try:
                operator = f"api_bot_{request.conversation_id}"
                await log_chip_load(
                    username=request.username,
                    operator=operator,
                    amount=request.amount,
                    bonus_percentage=request.bonus_percentage,
                    load_type="bonus"
                )
                logger.info(f"Bonus load logged to Google Sheets: {request.amount} + {request.bonus_percentage}% bonus to {request.username}")
            except Exception as e:
                logger.error(f"Failed to log bonus load to Google Sheets: {e}")
                # Continue with success response even if logging fails

            response = BalanceLoadResponse(
                status="success",
                username=request.username,
                amount_loaded=request.amount,
                bonus_amount=request.bonus_percentage,
                response_message=f"Successfully loaded {request.amount} pesos + {request.bonus_percentage}% bonus to {request.username}"
            )
            logger.info(f"Bonus load successful: {request.amount} + {request.bonus_percentage}% bonus to {request.username}")
            return response

        else:
            # Transaction failed
            response = BalanceLoadResponse(
                status="error",
                username=request.username,
                response_message="Failed to load balance with bonus",
                error_detail=message
            )
            logger.error(f"Bonus load failed: {request.username} - {message}")
            return response
                
    except Exception as e:
        logger.error(f"API error loading bonus balance to {request.username}: {str(e)}")
        response = BalanceLoadResponse(
            status="error",
            username=request.username,
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
            "load_balance": "/api/load-balance",
            "load_balance_bonus": "/api/load-balance-bonus",
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