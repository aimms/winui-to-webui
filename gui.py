import winui_to_webui 
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QFileDialog, QMessageBox
)
from PySide6.QtGui import QFont


class ConverterApp(QWidget):
    def __init__(self) -> None:
        """
        Initialize the converter application window and set up its interface.
        
        :return: None. Configures the QWidget and loads the initial UI layout.
        :rtype: None
        """
        super().__init__()
        self.setWindowTitle("WinUI to WebUI")
        self.init_ui()

    def init_ui(self) -> None:
        """
        Build the layout for selecting a project folder, entering the project file, and running the conversion.
        
        :return: None. Populates the widget with inputs and buttons.
        :rtype: None
        """
        # # Create the container widget
        # parent_widget = QWidget()

        # # Set the style using a stylesheet on the parent
        # # This style will apply to ALL widgets inside this QWidget
        # parent_widget.setStyleSheet("QWidget { font-size: 14px; }")

        layout = QVBoxLayout()
        
        # Folder Selection
        self.folder_line = QLineEdit("Select AIMMS Project folder...")
        btn_folder = QPushButton("Select Folder")
        btn_folder.clicked.connect(self.select_folder)
        layout.addWidget(self.folder_line)
        layout.addWidget(btn_folder)

        # File Input
        self.file_line = QLineEdit("Enter project_name without .aimms...")
        layout.addWidget(self.file_line)

        # Run Button
        btn_run = QPushButton("Run Conversion")
        btn_run.clicked.connect(self.run_conversion)
        layout.addWidget(btn_run)
        
        self.setLayout(layout)

    def select_folder(self) -> None:
        """
        Open a directory chooser and populate the folder input with the selected path.
        
        :return: None. Updates the folder line edit when a folder is chosen.
        :rtype: None
        """
        folder = QFileDialog.getExistingDirectory(self, "Select AIMMS Project Folder")
        if folder:
            self.folder_line.setText(folder)

    def run_conversion(self) -> None:
        """
        Validate input values and run the WinUI-to-WebUI conversion for the chosen project.
        
        :return: None. Triggers the conversion workflow or shows an error dialog when inputs are missing.
        :rtype: None
        """
        folder = self.folder_line.text()
        filename = self.file_line.text()
        
        if not all([folder, filename]):
            QMessageBox.critical(self, "Error", "Please select a folder and enter a filename.")
            return

        # Call the core logic function
        winui_to_webui.process_aimms_app(folder, filename)
        # QMessageBox.information(self, "Result", result_message)

def gui_entry_point() -> None:
    """
    Launch the GUI entry point for the WinUI-to-WebUI converter application.
    
    :return: None. Starts the Qt event loop.
    :rtype: None
    """
    app = QApplication(sys.argv)
    window = ConverterApp()
    window.show()
    sys.exit(app.exec())
