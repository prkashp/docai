# Document AI Archive -  Claims Processing

This archive contains the previous implementation of the Document AI claims processing pipeline for  Health. It serves as a reference for the architecture and patterns used in processing insurance claims (professional, dental, and institutional).

## Overview

The archive consists of a complete Airflow DAG-based pipeline that:
- Preprocesses raw claim documents (unzipping, classification)
- Processes documents through Google Cloud Document AI
- Extracts structured data from claims
- Postprocesses results (scoring, standardization, B2B formatting)
- Loads results to Snowflake

## Architecture

### Directory Structure

```
archive/
├── docai__claims_process.py  # Main Airflow DAG
├── core/                              # Core claim processing models
│   ├── professional_claims_model.py   # Professional claims processor
│   ├── dental_claims_model.py         # Dental claims processor
│   └── institutional_claims_model.py  # Institutional claims processor
├── preprocessor/                      # Document preprocessing
│   ├── preprocessor_model.py          # Main preprocessor
│   ├── classifier.py                  # Document classification
│   ├── unzipper.py                    # Zip file extraction
│   └── utils.py                       # Utility functions
└── postprocessor/                     # Results postprocessing
    ├── postprocessor.py               # Main postprocessor
    ├── calculate_score.py             # Scoring logic
    ├── move_file.py                   # File movement logic
    ├── B2B.py                         # B2B format conversion
    ├── calling_*.py                   # Wrapper scripts
    └── dental/                        # Dental-specific postprocessing
        ├── s3_to_edi.py               # S3 to EDI format conversion
        └── json_standardization.py    # JSON standardization
```

### Key Components

#### 1. **Airflow DAG** (`docai__claims_process.py`)
- Orchestrates the entire pipeline
- Scheduled to run daily at 10:40 PM EST
- Handles task dependencies and error notifications
- Currently has `SKIP_ALL_TASKS = True` (disabled)

#### 2. **Preprocessor** (`preprocessor/`)
- **unzipper.py**: Extracts raw claim documents from ZIP files
- **classifier.py**: Classifies documents by type (professional, dental, institutional)
- **preprocessor_model.py**: Orchestrates preprocessing workflow

#### 3. **Core Models** (`core/`)
- Process documents through Google Cloud Document AI
- Extract structured data (claims information, patient data, etc.)
- **Snowflake Integration**: Each model uploads results to Snowflake via `get_snowflake_connection()`
- Supported claim types:
  - Professional claims
  - Dental claims
  - Institutional claims

#### 4. **Postprocessor** (`postprocessor/`)
- **calculate_score.py**: Computes confidence/quality scores
- **move_file.py**: Moves processed files to appropriate locations
- **B2B.py**: Converts results to B2B interchange format
- **Dental-specific processing**: EDI format conversion and JSON standardization

## Dependencies

### Current Stack
- **Orchestration**: Apache Airflow
- **Document AI**: Google Cloud Document AI
- **Database**: Snowflake (for result storage)
- **Cloud Storage**: AWS S3
- **Environment**: Python-based microservices

### Known Dependencies
- `utils.get_snowflake_connection()`: Provides Snowflake database connections
- Google Cloud credentials for Document AI access
- AWS credentials for S3 access

## Future Improvements

### Priority: Remove Snowflake Dependency
**Rationale**: Reduce external dependencies and enable offline/local processing

**Approach**:
- Replace Snowflake writes with file-based outputs (JSON, Parquet, CSV)
- Store results in local/S3 locations instead of database
- Maintain same data schema for backward compatibility

### Priority: Implement Offline OCR Model
**Rationale**: Reduce latency, cost, and cloud dependency for basic document extraction

**Candidates**:
- **PaddleOCR**: Fast, multilingual, can run locally
- **EasyOCR**: Simple API, good accuracy
- **Tesseract**: Traditional but reliable
- **LayoutLM**: Document understanding with layout awareness

**Implementation**:
- Use offline OCR for initial text extraction
- Route complex cases to Google Cloud Document AI
- Hybrid approach: OCR + validation/enrichment via Cloud AI

## Important Notes

⚠️ **This is an archive folder** - DO NOT build upon or reuse this code directly without understanding the context and limitations.

### Why It's Archived
- Built for specific  Health requirements
- Heavy Snowflake coupling
- Can serve as reference for architecture patterns and claim processing logic

### Before Reusing Any Code
1. Review the specific business logic for your use case
2. Update dependencies to latest versions
3. Remove or replace Snowflake integration
4. Add error handling and logging for production use
5. Update credentials/environment configuration
6. Test with current Google Cloud Document AI APIs

## Getting Started (For Reference Only)

If you need to understand the processing workflow:

1. **Pipeline Flow**: Start with `docai__claims_process.py` to understand task dependencies
2. **Document Flow**: Follow `preprocessor/preprocessor_model.py` to see preprocessing steps
3. **Data Extraction**: Review relevant model in `core/` for your claim type
4. **Result Handling**: Check `postprocessor/` for result formatting and storage

## Questions?

Refer to the individual module docstrings and inline comments for specific implementation details. The code is archived but reasonably well-documented for reference purposes.
