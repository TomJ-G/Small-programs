__author__ = "Tomasz Galica"
__license__ = "GNU"

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QDialog, QSplitter
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
import os
import json

class HTMLViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.file_list = []
        self.current_index = 0
        self.annotation_dir = ""  # Directory to save annotations
        self.json_dir = ""  # Directory to find JSON files

        self.initUI()

    def initUI(self):
        self.setWindowTitle("HTML and JSON Viewer")
        self.setGeometry(100, 100, 1200, 800)

        # Create the main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Create a splitter to separate HTML and JSON display areas
        self.splitter = QSplitter(Qt.Horizontal)

        # Create the QWebEngineView to display HTML content
        self.web_view = QWebEngineView(self)
        self.splitter.addWidget(self.web_view)

        # Create a QTextEdit widget to display JSON content
        self.json_view = QTextEdit(self)
        self.json_view.setReadOnly(True)
        self.splitter.addWidget(self.json_view)

        # Set the initial splitter ratio
        self.splitter.setSizes([600, 600])

        # Add the splitter to the main layout
        self.main_layout.addWidget(self.splitter)

        # Create a horizontal layout for the label and buttons
        self.top_layout = QHBoxLayout()
        self.main_layout.addLayout(self.top_layout)

        # Create a label to show the current file name
        self.label = QLabel("", self)
        self.label.setMaximumHeight(20)
        self.top_layout.addWidget(self.label)

        # Create a button to load HTML files
        self.load_button = QPushButton("Load HTML Files", self)
        self.load_button.clicked.connect(self.load_files)
        self.top_layout.addWidget(self.load_button)

        # Create a QTextEdit widget for annotations
        self.annotation_text = QTextEdit(self)
        self.annotation_text.setPlaceholderText("Write your annotation here...")
        self.annotation_text.setMaximumHeight(400)
        self.main_layout.addWidget(self.annotation_text)

        # Create a button to open HTML as text
        self.open_as_text_button = QPushButton("Open HTML as Text", self)
        self.open_as_text_button.clicked.connect(self.open_as_text)
        self.open_as_text_button.setMaximumHeight(30)
        self.top_layout.addWidget(self.open_as_text_button)

        # Create a button to save annotation
        self.save_button = QPushButton("Save Annotation", self)
        self.save_button.clicked.connect(self.save_annotation)
        self.save_button.setMaximumHeight(30)
        self.top_layout.addWidget(self.save_button)

        # Enable keyboard navigation
        self.central_widget.setFocus()
        self.central_widget.keyPressEvent = self.keyPressEvent

    def load_files(self):
        """Select HTML tables to be viewed"""
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select HTML Files", "", "HTML Files (*.html);;All Files (*)", options=options)
        if files:
            self.file_list = files
            self.current_index = 0
            self.show_file(self.file_list[self.current_index])

            # Prompt user for the directory to save annotations
            self.annotation_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Annotations")
            if not self.annotation_dir:
                self.annotation_dir = ""  # Reset if no directory is chosen

            # Prompt user for the directory to find JSON files
            self.json_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Find JSON Files")
            if not self.json_dir:
                self.json_dir = ""  # Reset if no directory is chosen

    def show_file(self, file_path):
        """Display HTML, JSON and corresponding annotation file"""
        file_name = os.path.basename(file_path)
        self.label.setText(f"Viewing: {file_name}")
        self.web_view.setUrl(QUrl.fromLocalFile(file_path))

        # Load the corresponding JSON file if available
        json_file = os.path.join(self.json_dir, f"{os.path.splitext(file_name)[0]}.json")
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
                formatted_json = json.dumps(json_data, indent=4)
                self.json_view.setPlainText(formatted_json)
        else:
            self.json_view.setPlainText("")
        self.statusBar().showMessage(f"File {self.current_index+1}/{len(self.file_list)}")

        # Load existing annotation if available
        annotation_file = os.path.join(self.annotation_dir, f"{os.path.splitext(file_name)[0]}.txt")
        if os.path.exists(annotation_file):
            with open(annotation_file, 'r', encoding='utf-8') as file:
                self.annotation_text.setPlainText(file.read())
        else:
            self.annotation_text.clear()

    def save_annotation(self):
        """Save annotation in txt format"""
        if self.file_list:
            current_file_path = self.file_list[self.current_index]
            file_name = os.path.basename(current_file_path)
            annotation_file = os.path.join(self.annotation_dir, f"{os.path.splitext(file_name)[0]}.txt")

            # Save the annotation to the specified file
            with open(annotation_file, 'w', encoding='utf-8') as file:
                file.write(self.annotation_text.toPlainText())
            self.statusBar().showMessage(f"Annotation saved to {annotation_file}")


    def keyPressEvent(self, event):
        key = event.key()
        if key == 16777236:  # Right arrow key
            self.next_file()
        elif key == 16777234:  # Left arrow key
            self.prev_file()

    def next_file(self):
        if self.file_list and self.current_index < len(self.file_list) - 1:
            self.current_index += 1
            self.show_file(self.file_list[self.current_index])

    def prev_file(self):
        if self.file_list and self.current_index > 0:
            self.current_index -= 1
            self.show_file(self.file_list[self.current_index])


    def open_as_text(self):
        # Show raw HTML code
        if self.file_list:
            current_file_path = self.file_list[self.current_index]
            file_name = os.path.basename(current_file_path)

            # Create a dialog to show the HTML file as plain text
            text_dialog = QDialog(self)
            text_dialog.setWindowTitle(f"Text View: {file_name}")
            text_dialog.setGeometry(100, 100, 1024, 600)

            # Create a QTextEdit widget inside the dialog
            text_edit = QTextEdit(text_dialog)
            text_edit.setGeometry(10, 10, 1014, 590)
            text_edit.setReadOnly(True)

            # Load the HTML file content as plain text
            with open(current_file_path, 'r', encoding='utf-8') as file:
                text_edit.setPlainText(file.read())

            text_dialog.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = HTMLViewer()
    viewer.show()
    sys.exit(app.exec_())
