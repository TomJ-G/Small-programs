### Purpose 
Program was made for users who prefer to use GUI instead of command line (or non-programmers).
It can subtract background from signal spectra and calculate the intensity difference via line method.

### Data reading
Two files need to be read-in to the program: background and signal files. Both files should be in common txt format, where columns of data are separated with semicolon. Program will try to guess the number of columns in file, and retreive headers. We assume that there are at least two header lines: column names and units. The first column is used as a X value and last column is used as Y value. Both background and signal should have the same x-axis values.

### How to pick points for line method?
User can click on the plot to select two points. By default program will try to snap to the nearest datapoints. This behavior can be changed to snapping to the nearest local maximum (see the checkbox in the top right corner).
