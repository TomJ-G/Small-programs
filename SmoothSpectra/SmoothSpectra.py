__author__ = "Tomasz Galica"
__license__ = "GNU"

from sys import argv, exit
from numpy import abs, argmax, genfromtxt, array, where
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QSpinBox, QCheckBox
)

from scipy.signal import savgol_filter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseButton
from scipy.signal import find_peaks



#TODO:
# 1) Make the script only need to pick up the background file and automatically pair it with signal file.

def is_number(element: any) -> bool:
    #If you expect None to be passed:
    if element is None: 
        return False
    try:
        float(element)
        return True
    except ValueError:
        try:
            int(element)
            return True
        except ValueError:
            return False


def process_data(path):
    """
    This function performs initial preprocessing of a txt file into NumPy arrays.
    Parameters: 
    - path: Path to the file with data
    
    Returns: 
    - wavelength: NumPy array of the first column (index)
    - reflectance: NumPy array of the last column (data)
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = f.readlines()

    # Detect the most frequent number of columns (width)
    detect_cols_n = {}
    for line in data:
        cols_count = len(line.split(";"))
        detect_cols_n[cols_count] = detect_cols_n.get(cols_count, 0) + 1
    
    # Determine the width by the most frequent number of columns
    width = max(detect_cols_n, key=detect_cols_n.get)
    
    if width == 1:
        # If width is 1, skip first 7 rows and load the data directly
        raw_data = genfromtxt(path, delimiter=";", skip_header=7)
    else:
        # Process the lines with the detected width
        processed_lines = [line.replace(",", ".").split(";") for line in data if len(line.split(";")) == width]
        processed_lines = array(processed_lines)

        # Find the row where numerical data starts
        num_start = 0
        for i, line in enumerate(processed_lines):
            if all([is_number(val) for val in line]):
                num_start = i
                break

        # Merge headers if they exist
        headers = [''] * width
        for i in range(num_start):
            headers = [" ".join(filter(None, [h.strip(), line.strip()])) for h, line in zip(headers, processed_lines[i])]
        
        # Extract the data rows starting from the first row with numerical values
        raw_data = processed_lines[num_start:].astype(float)
    
    # Assume first column is wavelength and last one is reflectance
    wavelength = raw_data[:, 0]  # First column
    reflectance = raw_data[:, -1]  # Last column

    return ((headers[0],wavelength), (headers[-1],reflectance))


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.line = None
        self.selected_points = []

        # New attributes for text fields showing cursor position
        self.cursor_x_label = QLabel('Cursor X:')
        self.cursor_y_label = QLabel('Cursor Y:')
        self.cursor_x_value = QLineEdit(self)
        self.cursor_y_value = QLineEdit(self)
        self.cursor_x_value.setReadOnly(True)
        self.cursor_y_value.setReadOnly(True)

    def initUI(self):
        self.setWindowTitle('SmoothSpectra')

        # Main layout
        layout = QVBoxLayout(self)

        # Load buttons
        btn_layout = QHBoxLayout()
        btn_layout.SetMaximumSize = [20,20]
        self.btn_load_file1 = QPushButton('Load background')
        self.btn_load_file2 = QPushButton('Load signal')
        self.btn_load_file1.clicked.connect(self.load_file1)
        self.btn_load_file2.clicked.connect(self.load_file2)
        btn_layout.addWidget(self.btn_load_file1)
        btn_layout.addWidget(self.btn_load_file2)
        layout.addLayout(btn_layout)

        # Submit and compute difference button
        self.btn_submit = QPushButton('Compute Difference')
        self.btn_submit.clicked.connect(self.compute_difference)
        btn_layout.addWidget(self.btn_submit)

        # Smoothing button
        self.btn_smooth = QPushButton('Smooth')
        self.btn_smooth.clicked.connect(self.smooth)
        btn_layout.addWidget(self.btn_smooth)

        # Spin-box with parameter for savgol 
        self.sawgol_window = QSpinBox()
        self.sawgol_window.setValue(50)
        self.sawgol_window.setMinimum(3)
        self.sawgol_window.setMaximum(500)
        btn_layout.addWidget(self.sawgol_window)

        # Switch snapping method
        self.SnapMax = QCheckBox("Snap to local maxima", self)
        btn_layout.addWidget(self.SnapMax)

        # Matplotlib canvas for plotting
        self.figure = Figure(layout='tight')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas,stretch=2)

        # Interactive selection
        select_layout = QHBoxLayout()
        select_layout.SetMaximumSize = [20,20]
        self.input_x1 = QLineEdit()
        self.input_x2 = QLineEdit()
        self.label_diff = QLabel('Reflectance: ----')
        select_layout.addWidget(QLabel('X1:'))
        select_layout.addWidget(self.input_x1)
        select_layout.addWidget(QLabel('X2:'))
        select_layout.addWidget(self.input_x2)
        select_layout.addWidget(self.label_diff)
        layout.addLayout(select_layout)

        # 2nd set of buttons
        btn_below_layout = QHBoxLayout()
        btn_below_layout.SetMaximumSize = [20,20]

        # Connect the save button to the save_diff_to_file method
        self.save_btn = QPushButton('Save diff curve')
        self.save_btn.clicked.connect(self.save_diff_to_file)
        btn_below_layout.addWidget(self.save_btn)

        # Calculate reflectance
        self.calc_ref = QPushButton('Calculate refl.')
        self.calc_ref.clicked.connect(self.get_reflectance)
        btn_below_layout.addWidget(self.calc_ref)

        # Save reflectance data
        self.save_refl = QPushButton('Save reflectance')
        self.save_refl.clicked.connect(self.save_refl_to_file)
        btn_below_layout.addWidget(self.save_refl)

        # Add button layout to main layout
        layout.addLayout(btn_below_layout)

        # Initial data
        self.df1 = None
        self.df2 = None
        self.df_diff = None
        self.smoothed = None
        self.stored = None
        self.x_range = [None,None]
        self.line_eq = None
        self.reflectance = None
        self.i_line = None
        self.df_reflectance = None
        self.index_name = None
        self.column_name = None

        # Connect the mouse movement event to update cursor position
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        FigureCanvas.updateGeometry(self)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.show()
    

    def compute_difference(self):
        """Compute the differential curve"""
        if self.df1 is not None and self.df2 is not None:
            # We assume that background and signal have the same wavelength range
            self.df_diff = [self.df1[0][1],self.df1[1][1] - self.df2[1][1]]
            self.stored =  self.df_diff.copy()
            self.index_name = self.df1[0][0]
            self.column_name = self.df1[1][0]
            self.update_plot()


    def draw_line_between_points(self):
        """Draws a line between two selected points."""
        if len(self.selected_points) == 2:
            # Clear the previous line if it exists
            if self.line:
                self.line.remove()

            ax = self.figure.gca()
            x_values, y_values = zip(*self.selected_points)
            self.line, = ax.plot(x_values, y_values, 'r--')  # Red dashed line
            self.canvas.draw()
            # Clear selected points after drawing
            self.selected_points = []


    def draw_line_intensities(self,x):
        """Draws a line for highest reflectance."""
        
        # Clear the previous line if it exists
        if self.i_line:
            self.i_line.remove()

        ax = self.figure.gca()
        self.i_line = ax.axvline(x, color='#AAAAAA')  # grey line
        self.canvas.draw()


    def get_line(self,x1,x2):
        """Calculate line equation"""
        idx1 = where(self.df_diff[0]==x1)[0][0]
        idx2 = where(self.df_diff[0]==x2)[0][0]
        y1 = self.df_diff[1][idx1]
        y2 = self.df_diff[1][idx2]
        a = (y2 - y1) / (x2 - x1)
        b = y1 - a * x1
        return(a,b)


    def get_reflectance(self):
        """Calculates the reflectance with line method"""
        if self.line_eq:
            values = []
            a, b = self.line_eq
            idx1 = where(self.df_diff[0]==self.x_range[0])[0][0]
            idx2 = where(self.df_diff[0]==self.x_range[1])[0][0]

            temp = []
            for i in range(idx1,idx2+1):
                y_line   = a*self.df_diff[0][i]+b
                y_signal = self.df_diff[1][i]
                values.append(y_line-y_signal)
                temp.append([self.df_diff[0][i],values[-1]])
            self.df_reflectance = temp.copy()
            self.reflectance = max(values)
            
            # Draw line where reflectance was calculated
            n = argmax(values)
            self.draw_line_intensities(self.df_reflectance[n][0])
            
            try:
                self.label_diff.setText(f'Reflectance: {round(self.reflectance,4)}')
            except Exception as e:
                self.label_diff.setText('Reflectance: ----')


    def load_file1(self):
            # Load reference (before UV)
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getOpenFileName(self, "Load background file", "", "Text Files (*.txt);;All Files (*)", options=options)
            if file_name:
                self.df1 = process_data(file_name)
                self.update_plot()


    def load_file2(self):
        # Load signal (after UV)
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load signal file", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            self.df2 = process_data(file_name)
            self.update_plot()

    # Remove the function below at later stage - not needed anymore
    def on_mouse_move(self, event):
        """Updates cursor position fields as the mouse moves."""
        if event.inaxes:
            self.cursor_x_value.setText(f'{event.xdata:.2f}')
            self.cursor_y_value.setText(f'{event.ydata:.2f}')
        else:
            self.cursor_x_value.clear()
            self.cursor_y_value.clear()


    def on_click(self, event):
        """Handles mouse clicks on the plot."""
        if event.button == MouseButton.LEFT:
            x_click = event.xdata
            y_click = event.ydata

            if x_click is not None and y_click is not None:
                # Snap to the closest point or peak on the curve
                if self.SnapMax.isChecked() == True:
                    x_closest, y_closest = self.snap_to_closest_maximum(x_click, y_click)
                else:
                    x_closest, y_closest = self.snap_to_closest_point(x_click, y_click)
                self.selected_points.append((x_closest, y_closest))

                # Update the corresponding X1 and X2 fields based on number of clicks
                if len(self.selected_points) == 1:
                    self.input_x1.setText(f'{x_closest:.2f}')
                    self.x_range[0] = x_closest
                elif len(self.selected_points) == 2:
                    # Prevent selecting the same point twice
                    if self.selected_points[0] == self.selected_points[1]:
                        self.selected_points.pop()
                    else:
                        self.input_x2.setText(f'{x_closest:.2f}')
                        self.x_range[1] = x_closest

                # When both points are selected, draw a line
                if len(self.selected_points) == 2:
                    self.draw_line_between_points()
                    # get x-range
                    self.line_eq = self.get_line(self.x_range[0],self.x_range[1])


    def smooth(self):
        """Smooths the function with Savitzky-Golay filter."""
        if self.stored:
            # Apply Savitzky-Golay filter on the second column (reflectance) of stored array
            smoothed_values = savgol_filter(self.stored[1], self.sawgol_window.value(), 2)
            # Combine the original index (wavelength) and smoothed values into df_diff
            self.df_diff[1] = smoothed_values
            self.update_plot()


    def snap_to_closest_point(self, x_click, y_click):
        """Find the closest datapoint on the curve to the clicked point."""
        x_values = self.df_diff[0]
        y_values = self.df_diff[1]

        # Find the index of the closest x-value
        idx = (abs(x_values - x_click)).argmin()

        return x_values[idx], y_values[idx]


    def snap_to_closest_maximum(self, x_click, y_click):
        """Find the closest local maximum on the curve to the clicked point."""
        x_values = self.df_diff[0]
        y_values = self.df_diff[1]

        # Find the indices of all local maxima
        peaks, _ = find_peaks(y_values)

        # Get the x and y values of the local maxima
        peak_x_values = x_values[peaks]
        peak_y_values = y_values[peaks]

        # Find the index of the closest x-value among the local maxima
        idx = (abs(peak_x_values - x_click)).argmin()

        # Return the x and y value of the closest local maximum
        return peak_x_values[idx], peak_y_values[idx]


    def save_refl_to_file(self):
        """Saves only the reflectance to file"""
        if self.reflectance:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    n1,u1 = self.index_name.split(' ')
                    n2,u2 = self.column_name.split(' ')
                    f.write(f"{n1}   ;{n2}\n")
                    f.write(f"{u1}   ;{u2}\n")
                    for i in self.df_reflectance:
                        f.write(f"{i[0]:.6f};{i[1]:.6f}\n")


    def save_diff_to_file(self):
        """Saves the reflectance data to a text file with the specified header."""
        if self.df_diff != None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    n1,u1 = self.index_name.split(' ')
                    n2,u2 = self.column_name.split(' ')
                    f.write(f"{n1}   ;{n2}\n")
                    f.write(f"{u1}   ;{u2}\n")
                    for i in range(self.df_diff[0].shape[0]):
                        f.write(f"{self.df_diff[0][i]:.6f};{self.df_diff[1][i]:.6f}\n")


    def update_plot(self):
        self.figure.clear()
        if self.df_diff is not None:
            ax = self.figure.add_subplot(111)
            ax.plot(self.df_diff[0], self.df_diff[1])
            ax.set_xlabel(self.index_name)
            ax.set_ylabel(self.column_name)
            self.canvas.draw()
            # Make sure to reset selected points and remove any existing line when plot is updated
            self.selected_points = []
            if self.line:
                self.line.remove()
                self.line = None
            if self.i_line:
                self.i_line.remove()
                self.i_line = None


if __name__ == '__main__':
    app = QApplication(argv)
    ex = App()
    exit(app.exec_())
