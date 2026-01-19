# Bookmark Merger

A simple Python application to merge multiple Netscape-format bookmark HTML files (exported from browsers like Chrome, Firefox, Opera) into a single file, removing duplicates.

## Features

- GUI to select multiple files.
- Merges bookmarks into a single list.
- Deduplicates based on URL.
- Exports to a Netscape Bookmark HTML file importable by modern browsers.

## Running the Application

### From Source

1.  Install Python 3.13.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the script:
    ```bash
    python bookmark_merger.py
    ```

### Using the EXE

Run `dist/BookmarkMerger.exe`.

## Building the EXE

To build the executable yourself:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name BookmarkMerger --clean bookmark_merger.py
```

## Note

The application currently flattens all bookmarks into a single list to ensure all unique links are preserved without complex folder merging logic.
