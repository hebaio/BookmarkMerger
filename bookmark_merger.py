import sys
import os
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QListWidget, QPushButton, QFileDialog, QMessageBox, QAbstractItemView, QCheckBox)
from PySide6.QtCore import Qt

def parse_bookmarks(file_path):
    """
    Parses a Netscape format bookmark file.
    Returns a list of bookmark/folder dictionaries (hierarchical).
    """
    root_bookmarks = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
            dl = soup.find('dl')
            if dl:
                root_bookmarks = process_dl(dl)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return root_bookmarks

def process_dl(dl_element):
    items = []
    for child in dl_element.children:
        if child.name == 'dt':
            items.extend(process_dt(child))
        elif child.name == 'p':
            items.extend(process_container(child))
    return items

def process_container(element):
    items = []
    for child in element.children:
        if child.name == 'dt':
            items.extend(process_dt(child))
        elif child.name == 'p':
            items.extend(process_container(child))
    return items

def process_dt(dt_element):
    item = None
    
    # Check H3 (Folder) or A (Bookmark)
    h3 = dt_element.find('h3', recursive=False)
    a = dt_element.find('a', recursive=False)
    
    if h3:
        item = {
            'type': 'folder',
            'title': h3.get_text(),
            'add_date': h3.get('add_date'),
            'last_modified': h3.get('last_modified'),
            'children': []
        }
        dl = dt_element.find('dl', recursive=False)
        if dl:
            item['children'] = process_dl(dl)
            
    elif a:
        item = {
            'type': 'bookmark',
            'title': a.get_text(),
            'url': a.get('href'),
            'add_date': a.get('add_date'),
            'icon': a.get('icon')
        }
    
    result = []
    if item:
        result.append(item)
    
    # Process "siblings" buried in children (due to parser nesting)
    for child in dt_element.children:
        if child is h3 or child is a:
            continue
        if child.name == 'dl': 
            continue # Already handled as children
            
        if child.name == 'dt':
            result.extend(process_dt(child))
        elif child.name == 'p':
            result.extend(process_container(child))
            
    return result

def generate_netscape_html(bookmarks, output_file):
    """
    Generates a Netscape Bookmark file from a list of hierarchical bookmarks.
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
            write_items(f, bookmarks, 1)
            f.write(footer)
        return True
    except Exception as e:
        return str(e)

def write_items(f, items, indent_level):
    indent = "    " * indent_level
    for item in items:
        if item.get('type') == 'folder':
            title = escape_html(item.get('title', 'No Title'))
            add_date = item.get('add_date', '')
            last_modified = item.get('last_modified', '')
            
            attr_str = ''
            if add_date: attr_str += f' ADD_DATE="{add_date}"'
            if last_modified: attr_str += f' LAST_MODIFIED="{last_modified}"'
            
            f.write(f'{indent}<DT><H3{attr_str}>{title}</H3>\n')
            f.write(f'{indent}<DL><p>\n')
            write_items(f, item.get('children', []), indent_level + 1)
            f.write(f'{indent}</DL><p>\n')
            
        elif item.get('type') == 'bookmark':
            title = escape_html(item.get('title', 'No Title'))
            url = item.get('url', '')
            add_date = item.get('add_date', '')
            icon = item.get('icon', '')
            
            attr_str = f'HREF="{url}"'
            if add_date: attr_str += f' ADD_DATE="{add_date}"'
            if icon: attr_str += f' ICON="{icon}"'
            
            f.write(f'{indent}<DT><A {attr_str}>{title}</A>\n')

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
        self.chk_deduplicate.stateChanged.connect(self.toggle_criteria)
        layout.addWidget(self.chk_deduplicate)
        
        # Deduplication Criteria Layout
        self.criteria_group = QWidget()
        crit_layout = QHBoxLayout()
        crit_layout.setContentsMargins(20, 0, 0, 0) # Indent
        
        self.chk_crit_folder = QCheckBox("By Folder")
        self.chk_crit_folder.setToolTip("If checked, bookmarks in different folders are NOT duplicates.")
        crit_layout.addWidget(self.chk_crit_folder)
        
        self.chk_crit_title = QCheckBox("By Title")
        self.chk_crit_title.setToolTip("If checked, bookmarks must have matching Titles to be duplicates.")
        crit_layout.addWidget(self.chk_crit_title)
        
        self.chk_crit_url = QCheckBox("By URL")
        self.chk_crit_url.setChecked(True)
        self.chk_crit_url.setToolTip("If checked, bookmarks must have matching URLs to be duplicates.")
        crit_layout.addWidget(self.chk_crit_url)
        
        crit_layout.addStretch()
        self.criteria_group.setLayout(crit_layout)
        layout.addWidget(self.criteria_group)

        
        self.btn_merge = QPushButton("Merge and Save To...")
        self.btn_merge.clicked.connect(self.merge_bookmarks)
        self.btn_merge.setStyleSheet("background-color: #0078d7; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(self.btn_merge)
        
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
        layout.addWidget(self.status_lbl)
        
        self.setLayout(layout)

    def toggle_criteria(self, state):
        self.criteria_group.setEnabled(state == Qt.Checked.value)

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
            
        remove_duplicates = self.chk_deduplicate.isChecked()
        crit_folder = self.chk_crit_folder.isChecked()
        crit_title = self.chk_crit_title.isChecked()
        crit_url = self.chk_crit_url.isChecked()
        
        if remove_duplicates and not (crit_folder or crit_title or crit_url):
            QMessageBox.warning(self, "Criteria Missing", "Please select at least one duplicate removal criteria (Folder, Title, or URL).")
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

        seen_keys = set()
        merged_bookmarks = []
        duplicate_count = 0
        
        def get_key(item, path):
            k = []
            if crit_folder:
                k.append(path)
            if crit_url:
                k.append(item.get('url'))
            if crit_title:
                k.append(item.get('title'))
            return tuple(k)

        def recursive_merge(target, source, current_path=()):
            nonlocal duplicate_count
            for item in source:
                if item['type'] == 'folder':
                    # Check if folder exists in target
                    found = None
                    folder_title = item.get('title', 'No Title')
                    
                    # Merge folders if they have same title (always merge structure)
                    for t in target:
                        if t['type'] == 'folder' and t['title'] == folder_title:
                            found = t
                            break
                    if found:
                        recursive_merge(found['children'], item['children'], current_path + (folder_title,))
                    else:
                        new_folder = {
                            'type': 'folder',
                            'title': folder_title,
                            'add_date': item.get('add_date'),
                            'last_modified': item.get('last_modified'),
                            'children': []
                        }
                        target.append(new_folder)
                        recursive_merge(new_folder['children'], item['children'], current_path + (folder_title,))
                        
                elif item['type'] == 'bookmark':
                    if remove_duplicates:
                        key = get_key(item, current_path)
                        if key in seen_keys:
                            duplicate_count += 1
                        else:
                            seen_keys.add(key)
                            target.append(item)
                    else:
                        target.append(item)

        for file_path in self.file_list:
            bookmarks = parse_bookmarks(file_path)
            recursive_merge(merged_bookmarks, bookmarks)
        
        result = generate_netscape_html(merged_bookmarks, save_path)

        
        if result is True:
            QMessageBox.information(self, "Success", f"Successfully merged bookmarks.\nIgnored {duplicate_count} duplicates.\nSaved to: {save_path}")
            self.status_lbl.setText("Merge complete.")
        else:
            QMessageBox.critical(self, "Error", f"Failed to save file: {result}")
            self.status_lbl.setText("Error during merge.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = BookmarkMergerApp()
    ex.show()
    sys.exit(app.exec())
