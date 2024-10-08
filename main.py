import ee
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import json
from src.api_routes import router
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account

# Initialize Earth Engine
#ee.Initialize(project='ee-mazikuben2')

# Load environment vation.")riables from .env file
service_account = 'test-724@ee-mazikuben2.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, 'credentials.json')
ee.Initialize(credentials)

    
    

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Farm Analysis API",
              description="API for analyzing farm vegetation and climate data using Google Earth Engine and NASA data sources.",
              version="1.0.0")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
