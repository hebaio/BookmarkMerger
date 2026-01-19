import sys
import os
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QListWidget, QPushButton, QFileDialog, QMessageBox, QAbstractItemView, QCheckBox)
from PySide6.QtCore import Qt

def parse_bookmarks(file_path):
    """
    Parses a Netscape format bookmark file.
    Returns a list of bookmark dictionaries.
    """
    bookmarks = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
            for link in soup.find_all('a'):
                url = link.get('href')
                title = link.get_text()
                add_date = link.get('add_date')
                icon = link.get('icon')
                
                if url:
                    bookmarks.append({
                        'url': url,
                        'title': title,
                        'add_date': add_date,
                        'icon': icon
                    })
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return bookmarks

def generate_netscape_html(bookmarks, output_file):
    """
    Generates a Netscape Bookmark file from a list of bookmarks.
    """
    header = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
     It will be read and overwritten.
     DO NOT EDIT! -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
"""
    footer = "</DL><p>"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)
            for b in bookmarks:
                url = b.get('url', '')
                title = b.get('title', 'No Title')
                add_date = b.get('add_date', '')
                icon = b.get('icon', '')
                
                # Construct attributes
                attr_str = f'HREF="{url}"'
                if add_date:
                    attr_str += f' ADD_DATE="{add_date}"'
                if icon:
                    attr_str += f' ICON="{icon}"'
                
                # Escape title for HTML to be safe
                safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                f.write(f'    <DT><A {attr_str}>{safe_title}</A>\n')
                
            f.write(footer)
        return True
    except Exception as e:
        return str(e)

class BookmarkMergerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.file_list = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Bookmark Merger')
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        self.lbl_instruction = QLabel("Select bookmark HTML files to merge:")
        layout.addWidget(self.lbl_instruction)
        
        self.listbox = QListWidget()
        self.listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.listbox)
        
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Add Files...")
        self.btn_add.clicked.connect(self.add_files)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_files)
        btn_layout.addWidget(self.btn_remove)
        
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.btn_clear)
        
        layout.addLayout(btn_layout)

        self.chk_deduplicate = QCheckBox("Remove Duplicates")
        self.chk_deduplicate.setChecked(True)
        layout.addWidget(self.chk_deduplicate)
        
        self.btn_merge = QPushButton("Merge and Save To...")
        self.btn_merge.clicked.connect(self.merge_bookmarks)
        self.btn_merge.setStyleSheet("background-color: #0078d7; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(self.btn_merge)
        
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
        layout.addWidget(self.status_lbl)
        
        self.setLayout(layout)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Bookmark Files",
            "",
            "HTML Files (*.html *.htm);;All Files (*.*)"
        )
        if files:
            for f in files:
                if f not in self.file_list:
                    self.file_list.append(f)
                    self.listbox.addItem(f)
            self.status_lbl.setText(f"{len(self.file_list)} files selected.")

    def remove_files(self):
        selected_items = self.listbox.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.listbox.row(item)
            self.listbox.takeItem(row) # Removes from widget
            # To remove from self.file_list, we need to be careful about synchronization
            # Simpler to reconstruct list from widget
        
        # Rebuild file_list from widget items
        self.file_list = []
        for i in range(self.listbox.count()):
            self.file_list.append(self.listbox.item(i).text())
            
        self.status_lbl.setText(f"{len(self.file_list)} files selected.")

    def clear_list(self):
        self.file_list = []
        self.listbox.clear()
        self.status_lbl.setText("List cleared.")

    def merge_bookmarks(self):
        if not self.file_list:
            QMessageBox.warning(self, "No Files", "Please add at least one bookmark file to merge.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged Bookmarks",
            "",
            "HTML Files (*.html)"
        )
        
        if not save_path:
            return

        self.status_lbl.setText("Merging...")
        QApplication.processEvents()

        seen_urls = set()
        merged_bookmarks = []
        duplicate_count = 0
        remove_duplicates = self.chk_deduplicate.isChecked()

        for file_path in self.file_list:
            bookmarks = parse_bookmarks(file_path)
            for b in bookmarks:
                url = b.get('url')
                if not url:
                    continue

                if remove_duplicates:
                    if url not in seen_urls:
                        seen_urls.add(url)
                        merged_bookmarks.append(b)
                    else:
                        duplicate_count += 1
                else:
                    merged_bookmarks.append(b)
        
        result = generate_netscape_html(merged_bookmarks, save_path)
        
        if result is True:
            QMessageBox.information(self, "Success", f"Successfully merged {len(merged_bookmarks)} bookmarks.\nIgnored {duplicate_count} duplicates.\nSaved to: {save_path}")
            self.status_lbl.setText("Merge complete.")
        else:
            QMessageBox.critical(self, "Error", f"Failed to save file: {result}")
            self.status_lbl.setText("Error during merge.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = BookmarkMergerApp()
    ex.show()
    sys.exit(app.exec())
