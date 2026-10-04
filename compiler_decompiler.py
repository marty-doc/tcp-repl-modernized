# -*- coding: utf-8 -*-
"""Python 2.7 Compiler/Decompiler GUI with batch operations.

Provides a simple Tkinter interface for compiling and decompiling
Python files and directories.
"""

import os
import sys
import threading
import py_compile
import Tkinter as tk
import tkFileDialog
import tkMessageBox

try:
    import uncompyle2
    HAS_UNCOMPYLE2 = True
except ImportError:
    HAS_UNCOMPYLE2 = False


class CompilerDecompiler(tk.Tk):
    """Main GUI application for compile/decompile operations."""

    def __init__(self):
        tk.Tk.__init__(self)
        self.title('Python Compiler/Decompiler')
        self.geometry('700x600')

        self.log_queue = []
        self._build_ui()

    def _build_ui(self):
        """Build the user interface."""
        # Top frame: buttons
        button_frame = tk.Frame(self, bg='#dddddd', height=80)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(
            button_frame, text='Compile Operations', font=('Arial', 10, 'bold'),
            bg='#dddddd'
        ).pack(fill=tk.X, padx=5, pady=(5, 3))

        row1 = tk.Frame(button_frame, bg='#dddddd')
        row1.pack(fill=tk.X, padx=5, pady=3)

        tk.Button(
            row1, text='Compile File', command=self._compile_file,
            width=20, bg='#90EE90'
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            row1, text='Compile Directory', command=self._compile_dir,
            width=20, bg='#90EE90'
        ).pack(side=tk.LEFT, padx=3)

        tk.Label(
            button_frame, text='Decompile Operations', font=('Arial', 10, 'bold'),
            bg='#dddddd'
        ).pack(fill=tk.X, padx=5, pady=(5, 3))

        row2 = tk.Frame(button_frame, bg='#dddddd')
        row2.pack(fill=tk.X, padx=5, pady=3)

        tk.Button(
            row2, text='Decompile File', command=self._decompile_file,
            width=20, bg='#87CEEB'
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            row2, text='Decompile Directory', command=self._decompile_dir,
            width=20, bg='#87CEEB'
        ).pack(side=tk.LEFT, padx=3)

        row3 = tk.Frame(button_frame, bg='#dddddd')
        row3.pack(fill=tk.X, padx=5, pady=3)

        tk.Button(
            row3, text='Clear Log', command=self._clear_log,
            width=20, bg='#FFB6C1'
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            row3, text='Save Log', command=self._save_log,
            width=20, bg='#FFFFE0'
        ).pack(side=tk.LEFT, padx=3)

        # Log frame
        log_label_frame = tk.Frame(self)
        log_label_frame.pack(fill=tk.X, padx=5, pady=(10, 2))

        tk.Label(
            log_label_frame, text='Operation Log', font=('Arial', 10, 'bold')
        ).pack(anchor='w')

        # Log text area with scrollbar
        log_frame = tk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log = tk.Text(
            log_frame, wrap=tk.WORD, font=('Courier', 9),
            yscrollcommand=log_scroll.set, height=20
        )
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log.yview)

        self.log.config(state=tk.DISABLED)

    def _log_write(self, text):
        """Write text to the log window."""
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, text)
        if not text.endswith('\n'):
            self.log.insert(tk.END, '\n')
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)
        self.update_idletasks()

    def _clear_log(self):
        """Clear the log window."""
        self.log.config(state=tk.NORMAL)
        self.log.delete('1.0', tk.END)
        self.log.config(state=tk.DISABLED)

    def _save_log(self):
        """Save log to file."""
        filepath = tkFileDialog.asksaveasfilename(
            title='Save log as',
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w') as f:
                f.write(self.log.get('1.0', tk.END))
            self._log_write('Log saved to: %s\n' % filepath)
        except Exception as exc:
            self._log_write('Error saving log: %s\n' % str(exc))

    def _compile_file(self):
        """Compile a single Python file."""
        filepath = tkFileDialog.askopenfilename(
            title='Select Python file to compile',
            filetypes=[('Python files', '*.py'), ('All files', '*.*')]
        )
        if not filepath:
            return

        thread = threading.Thread(target=self._compile_file_thread, args=(filepath,))
        thread.daemon = True
        thread.start()

    def _compile_file_thread(self, filepath):
        """Thread worker for compiling a single file."""
        self._log_write('Compiling: %s\n' % filepath)
        try:
            py_compile.compile(filepath, doraise=True)
            output_path = filepath + 'c'
            self._log_write('Success: %s -> %s\n' % (filepath, output_path))
        except py_compile.PyCompileError as exc:
            self._log_write('Error: %s\n' % str(exc))

    def _compile_dir(self):
        """Compile all Python files in a directory."""
        dirpath = tkFileDialog.askdirectory(title='Select directory to compile')
        if not dirpath:
            return

        thread = threading.Thread(target=self._compile_dir_thread, args=(dirpath,))
        thread.daemon = True
        thread.start()

    def _compile_dir_thread(self, dirpath):
        """Thread worker for compiling a directory."""
        self._log_write('Compiling directory: %s\n' % dirpath)
        count_success = 0
        count_error = 0

        for root, dirs, files in os.walk(dirpath):
            for filename in files:
                if filename.endswith('.py'):
                    filepath = os.path.join(root, filename)
                    try:
                        py_compile.compile(filepath, doraise=True)
                        self._log_write('  OK: %s\n' % filepath)
                        count_success += 1
                    except py_compile.PyCompileError as exc:
                        self._log_write('  ERROR: %s: %s\n' % (filepath, exc))
                        count_error += 1

        self._log_write('Compile complete: %d success, %d errors\n' % (
            count_success, count_error
        ))

    def _decompile_file(self):
        """Decompile a single .pyc file."""
        if not HAS_UNCOMPYLE2:
            tkMessageBox.showerror(
                'Error',
                'uncompyle2 module not installed.\n'
                'Install with: pip install uncompyle2'
            )
            return

        filepath = tkFileDialog.askopenfilename(
            title='Select .pyc file to decompile',
            filetypes=[('Compiled Python', '*.pyc'), ('All files', '*.*')]
        )
        if not filepath:
            return

        thread = threading.Thread(target=self._decompile_file_thread, args=(filepath,))
        thread.daemon = True
        thread.start()

    def _decompile_file_thread(self, filepath):
        """Thread worker for decompiling a single file."""
        if not HAS_UNCOMPYLE2:
            self._log_write('uncompyle2 not available\n')
            return

        output_path = os.path.splitext(filepath)[0] + '.py'
        self._log_write('Decompiling: %s\n' % filepath)

        try:
            with open(output_path, 'w') as output_file:
                uncompyle2.uncompyle_file(filepath, output_file)
            self._log_write('Success: %s -> %s\n' % (filepath, output_path))
        except Exception as exc:
            self._log_write('Error: %s\n' % str(exc))

    def _decompile_dir(self):
        """Decompile all .pyc files in a directory."""
        if not HAS_UNCOMPYLE2:
            tkMessageBox.showerror(
                'Error',
                'uncompyle2 module not installed.\n'
                'Install with: pip install uncompyle2'
            )
            return

        dirpath = tkFileDialog.askdirectory(
            title='Select directory to decompile'
        )
        if not dirpath:
            return

        thread = threading.Thread(target=self._decompile_dir_thread, args=(dirpath,))
        thread.daemon = True
        thread.start()

    def _decompile_dir_thread(self, dirpath):
        """Thread worker for decompiling a directory."""
        if not HAS_UNCOMPYLE2:
            self._log_write('uncompyle2 not available\n')
            return

        self._log_write('Decompiling directory: %s\n' % dirpath)
        count_success = 0
        count_error = 0

        for root, dirs, files in os.walk(dirpath):
            for filename in files:
                if filename.endswith('.pyc'):
                    pyc_path = os.path.join(root, filename)

                    # Preserve directory structure
                    rel_path = os.path.relpath(root, dirpath)
                    output_dir = os.path.join(dirpath, rel_path)

                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    py_name = filename[:-4] + '.py'
                    py_path = os.path.join(output_dir, py_name)

                    try:
                        with open(py_path, 'w') as output_file:
                            uncompyle2.uncompyle_file(pyc_path, output_file)
                        self._log_write('  OK: %s -> %s\n' % (pyc_path, py_path))
                        count_success += 1
                    except Exception as exc:
                        self._log_write(
                            '  ERROR: %s: %s\n' % (pyc_path, str(exc))
                        )
                        count_error += 1

        self._log_write('Decompile complete: %d success, %d errors\n' % (
            count_success, count_error
        ))


if __name__ == '__main__':
    app = CompilerDecompiler()
    app.mainloop()
