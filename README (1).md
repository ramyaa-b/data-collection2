# Text Classification Platform

A Streamlit-based manual text classification tool for labeling hate speech data.

## Features

✅ **Shared Progress Tracking** - Multiple devices work on the same queue (no duplicate work)
✅ **Auto-Resume** - Always continues from where you left off
✅ **Real-time Statistics** - Track completed, skipped, and category distribution
✅ **Original Label Display** - Shows the CSV's original label as a reference
✅ **Duplicate Handling** - Shows duplicate texts again for re-classification
✅ **Database Persistence** - All data stored in Supabase PostgreSQL

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Upload your CSV file to the correct location (or update the path in the code):
```python
CSV_FILE_PATH = "/mnt/user-data/uploads/Indo-HateSpeech_NoNormal.csv"
```

## Running the App

```bash
streamlit run classification_app.py
```

The app will open in your browser at `http://localhost:8501`

## How It Works

### Database Tables

1. **submissions** - Stores classified text
   - text: The text content
   - category: religion, gender, language_caste, normal
   - platform: Always "Reddit"
   - status: Always "pending"
   - timestamp: When it was classified

2. **classification_progress** - Tracks progress (shared across all devices)
   - current_row: Which row to show next
   - total_processed: Count of classified texts
   - total_skipped: Count of deleted/skipped texts
   - last_updated: Last action timestamp

### Workflow

1. App shows text from CSV row by row
2. You see the original label as a hint
3. Click one of 4 category buttons OR skip/delete
4. Classification saved to database immediately
5. Progress updates automatically
6. Next text appears instantly

### Multi-Device Usage

Since progress is stored in Supabase:
- Device A processes row 1 → Database updates to row 2
- Device B opens app → Starts from row 2
- Device C opens app → Starts from row 2 (same as B if B hasn't clicked yet)

**Note**: If two people click at the exact same time, both will save their classifications. This is by design (you wanted duplicates shown again).

## Statistics Shown

- Total rows in CSV
- Current row number
- Remaining rows
- Total completed
- Total skipped
- Per-category counts (Religion, Gender, Language/Caste, Normal)
- Progress bar with percentage

## Troubleshooting

**"Module not found" errors**:
```bash
pip install -r requirements.txt
```

**Database connection errors**:
- Check that Supabase URL is correct
- Ensure database allows connections from your IP

**CSV not found**:
- Update `CSV_FILE_PATH` in `classification_app.py` to your actual file path

## Resetting Progress

If you want to start over:
1. Complete all rows (or manually set current_row to total)
2. Click the "Reset Progress (Start Over)" button
3. This resets current_row, total_processed, and total_skipped to 0

## Security Note

⚠️ **WARNING**: The database credentials are hardcoded in the script. 

For production use:
1. Use environment variables
2. Create a `.env` file:
```
SUPABASE_DB_URL=postgresql://...
```

3. Update the code:
```python
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
```
