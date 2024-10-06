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

# Load environment variables from .env file
# Get Google credentials from the environment variable
google_credentials = os.getenv("GOOGLE_CREDENTIALS")

# Debug output (be careful not to log this in production)
print(f"Google credentials environment variable is {'set' if google_credentials else 'not set'}")

# Check if google_credentials is valid
if google_credentials:
    try:
        # Parse the JSON credentials
        credentials_dict = json.loads(google_credentials)
        print("Credentials parsed successfully.")
        
        # Initialize Earth Engine with the credentials
        credentials = ee.ServiceAccountCredentials(email=credentials_dict['client_email'], key_data=credentials_dict['private_key'])
        ee.Initialize(credentials)
        print("Earth Engine initialized successfully.")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    except ee.EEException as e:
        print(f"Error initializing Earth Engine: {e}")
else:
    print("Google credentials are not set. Please check your configuration.")
    
    

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