import pytesseract
from PIL import Image
from pathlib import Path

def extract_text(image_path: str) -> str:
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from {image_path}: {e}")
        return ""

def extract_text_from_directory(directory: str) -> dict:
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
    results = {}

    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Directory {directory} does not exist.")
        return results

    for file_path in dir_path.iterdir():
        if file_path.suffix.lower() in image_extensions:
            print(f"Processing {file_path.name}...")
            text = extract_text(str(file_path))
            results[file_path.name] = text

    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        text = extract_text(image_path)
        print(f"Extracted text from {image_path}:")
        print(text)
    else:
        print("Usage: python ocr.py <image_path>")
