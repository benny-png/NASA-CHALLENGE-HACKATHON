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


# Function to initialize Earth Engine with service account
def initialize_ee():
    try:
        # Try to initialize with application default credentials
        ee.Initialize(project='ee-mazikuben2')
        print("Initialized with application default credentials.")
    except ee.EEException:
        # If that fails, try to use service account
        try:
            service_account_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if service_account_file and os.path.exists(service_account_file):
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_file, 
                    scopes=['https://www.googleapis.com/auth/earthengine']
                )
                ee.Initialize(credentials, project='ee-mazikuben2')
                print(f"Initialized with service account: {service_account_file}")
            else:
                raise FileNotFoundError("Service account file not found.")
        except (FileNotFoundError, DefaultCredentialsError) as e:
            print(f"Failed to initialize Earth Engine: {str(e)}")
            print("Please ensure you have set up your credentials correctly.")
            raise

# Call this function at the start of your application
initialize_ee()

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