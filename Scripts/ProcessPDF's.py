import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from Scripts.AzureTextExtraction import extract_text_from_pdf, save_response_to_json

async def process_pdf(pdf_path: Path, output_base_dir: Path, endpoint: str, key: str):
    """
    Process a single PDF and save its JSON output.
    Maintains the folder structure relative to Data/Tickets.
    """
    # Calculate the relative path from the original Data/Tickets directory
    # E.g. Data/Tickets/29211/invoice.pdf -> 29211/invoice.pdf
    try:
        relative_path = pdf_path.relative_to(Path("Data/Tickets"))
    except ValueError:
        print(f"Skipping {pdf_path}: Not inside Data/Tickets.")
        return

    # Determine the new output path
    # E.g. Data/Output/29211/invoice.json
    output_json_path = output_base_dir / relative_path.with_suffix(".json")

    # Ensure the parent directory for the output file exists
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"⏳ Processing: {pdf_path}")
    print(f"   -> Saving to: {output_json_path}")

    try:
        # Call the extraction function from TextExtraction.py
        response = await extract_text_from_pdf(
            endpoint=endpoint,
            key=key,
            model_id="prebuilt-document",
            file_path=str(pdf_path)
        )
        
        # Save the result to the matching JSON file
        await save_response_to_json(response, str(output_json_path))
        print(f"✅ Successfully processed {pdf_path.name}\n")
        
    except Exception as e:
        print(f"❌ Error processing {pdf_path.name}: {e}\n")


async def main():
    # Load environment variables (useful if running directly without a loaded env)
    load_dotenv()

    endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_KEY")

    if not endpoint or not key:
        print("Error: AZURE_DOCUMENT_ENDPOINT or AZURE_DOCUMENT_KEY is missing in your environment/ .env file.")
        return

    tickets_dir = Path("Data/Tickets")
    output_dir = Path("Data/Output")

    if not tickets_dir.exists() or not tickets_dir.is_dir():
        print(f"Error: The directory {tickets_dir} does not exist.")
        return

    # Find all PDFs within Data/Tickets recursively
    pdf_files = list(tickets_dir.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {tickets_dir}.")
        return

    print(f"Found {len(pdf_files)} PDF files. Starting processing...\n")
    print("-" * 50)

    # Note: We process them sequentially to avoid hitting potential Azure rate limits (e.g., 429 Too Many Requests).
    # If your Azure tier allows high concurrency, we could use asyncio.gather() instead.
    for pdf_path in pdf_files:
        await process_pdf(pdf_path, output_dir, endpoint, key)

    print("-" * 50)
    print("Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
