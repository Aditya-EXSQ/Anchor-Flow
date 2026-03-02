import os
import json
import asyncio

import aiofiles
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

async def extract_text_from_pdf(endpoint: str, key: str, model_id: str, file_path: str) -> dict:
    """
    Call the Azure Form Recognizer endpoint to extract text and bounding boxes from a PDF asynchronously.

    Args:
        endpoint (str): The Azure Form Recognizer endpoint URL.
        key (str): The API key for authentication.
        model_id (str): The model ID to use (e.g., "prebuilt-document" or "prebuilt-read").
        file_path (str): Path to the input PDF file to be analyzed.

    Returns:
        dict: JSON-serializable dictionary containing the OCR results (including text contents and bounding boxes).
    """
    client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    async with client:
        async with aiofiles.open(file_path, "rb") as f:
            data = await f.read()

        poller = await client.begin_analyze_document(model_id=model_id, document=data)
        result = await poller.result()

    return result.to_dict()


async def save_response_to_json(response_data: dict, output_file_path: str) -> None:
    """
    Save the extracted Azure OCR response to a JSON file.

    Args:
        response_data (dict): The dictionary containing OCR results.
        output_file_path (str): Path to save the output JSON file.
    """
    async with aiofiles.open(output_file_path, "w") as f:
        await f.write(json.dumps(response_data, indent=4, default=str))

async def main():
    AZURE_DOCUMENT_ENDPOINT = os.getenv("AZURE_DOCUMENT_ENDPOINT")
    AZURE_DOCUMENT_KEY = os.getenv("AZURE_DOCUMENT_KEY")

    response = await extract_text_from_pdf(
        endpoint=AZURE_DOCUMENT_ENDPOINT,
        key=AZURE_DOCUMENT_KEY,
        model_id="prebuilt-document",
        file_path="Data/Tickets/29212/Main - Gator's Dockside - Q4'25.pdf"
    )
    
    await save_response_to_json(response, "output3.json")

if __name__ == "__main__":
    asyncio.run(main())