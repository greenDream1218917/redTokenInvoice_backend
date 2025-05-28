from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from dotenv import load_dotenv
import shutil
import json
import uuid

load_dotenv()
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility: Upload file to Pinata
def upload_file_to_pinata(file_path: str, filename: str):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_API_KEY
    }
    with open(file_path, "rb") as f:
        response = requests.post(url, files={"file": (filename, f)}, headers=headers)
    return response

# Utility: Upload JSON metadata to Pinata
def upload_json_to_pinata(metadata: dict):
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "Content-Type": "application/json",
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_API_KEY
    }
    response = requests.post(url, data=json.dumps(metadata), headers=headers)
    return response

@app.post("/mint")
async def mint_nft(
    name: str = Form(...),
    description: str = Form(...),
    payer: str = Form(...),
    issuer: str = Form(...),
    amount: str = Form(...),
    paytoken: str = Form(...),
    file: UploadFile = File(...)
):
    
    os.makedirs("uploads", exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = f"uploads/{temp_filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_response = upload_file_to_pinata(temp_path, temp_filename)
    os.remove(temp_path)  # Delete temp file

    if file_response.status_code != 200:
        return {"error": "File upload failed", "details": file_response.text}

    ipfs_hash = file_response.json()["IpfsHash"]
    image_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"

    metadata = {
        "name": name,
        "description": description,
        "image": image_url,
        "attributes": [
            {"trait_type": "payer", "value": payer},
            {"trait_type": "issuer", "value": issuer},
            {"trait_type": "amount", "value": amount},
            {"trait_type": "paytoken", "value": paytoken}
        ]
    }

    metadata_response = upload_json_to_pinata(metadata)

    if metadata_response.status_code != 200:
        return {"error": "Metadata upload failed", "details": metadata_response.text}

    metadata_hash = metadata_response.json()["IpfsHash"]
    metadata_url = f"https://gateway.pinata.cloud/ipfs/{metadata_hash}"

    return {
        "message": "NFT metadata uploaded successfully",
        "metadata_url": metadata_url,
        "image_url": image_url
    }