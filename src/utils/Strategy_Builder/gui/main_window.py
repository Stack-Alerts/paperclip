"""
Strategy Builder - Main Application Window

Tkinter-based GUI for visual strategy creation.

Author: Strategy Builder v2.0
Date: 2026-01-09
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.Strategy_Builder import (
    StrategyRegistry,
    StrategyValidator,
    StrategyGenerator
)


class StrategyBuilderApp:
    """Main application window for Strategy Builder GUI"""
    
    def __init__(self, root=None):
        """
        Initialize the application
        
        Args:
            root: Tkinter root window (creates new if None)
        """
        if root is None:
            self.root = tk.Tk()
            self.owns_root = True
        else:
            self.root = root
            self.owns_root = False
        
        self.root.title("Strategy Builder v2.0")
        self.root.geometry("1600x1000")
        self.root.minsize(1400, 900)
        
        # Configure much larger fonts (4x original)
        self.large_font = ('TkDefaultFont', 40)
        self.medium_font = ('TkDefaultFont', 32)
        self.small_font = ('TkDefaultFont', 28)
        self.button_font = ('TkDefaultFont', 28, 'bold')
        
        # VSCode Dark Mode Colors
        self.bg_dark = '#1e1e1e'  # Background
        self.bg_darker = '#252526'  # Darker sections
        self.fg_text = '#d4d4d4'  # Text color
        self.fg_bright = '#ffffff'  # Bright text
        self.accent = '#007acc'  # VS Code blue
        self.border = '#3e3e42'  # Borders
        
        # Apply dark theme
        self.root.configure(bg=self.bg_dark)
        
        # Initialize components
        self.registry = StrategyRegistry()
        self.validator = StrategyValidator()
        self.generator = StrategyGenerator()
        
        # Current strategy
        self.current_strategy = None
        
        # Build UI
        self._create_menu_bar()
        self._create_toolbar()
        self._create_main_layout()
        self._create_status_bar()
        
        # Load initial data
        self.refresh_strategy_list()
        
        # Center window
        self._center_window()
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Strategy", command=self.new_strategy, accelerator="Ctrl+N")
        file_menu.add_command(label="Save Strategy", command=self.save_strategy, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Generate Files", command=self.generate_files, accelerator="Ctrl+G")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Delete Strategy", command=self.delete_strategy, accelerator="Del")
        edit_menu.add_separator()
        edit_menu.add_command(label="Validate", command=self.validate_strategy, accelerator="F5")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh List", command=self.refresh_strategy_list, accelerator="F5")
        view_menu.add_command(label="Statistics", command=self.show_statistics)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_strategy())
        self.root.bind('<Control-s>', lambda e: self.save_strategy())
        self.root.bind('<Control-g>', lambda e: self.generate_files())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        self.root.bind('<Delete>', lambda e: self.delete_strategy())
        self.root.bind('<F5>', lambda e: self.refresh_strategy_list())
    
    def _create_toolbar(self):
        """Create toolbar with common actions"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Configure dark mode styles
        style = ttk.Style()
        style.theme_use('clam')  # Base theme that supports customization
        
        # Dark button style
        style.configure('Large.TButton', 
                       font=self.button_font, 
                       padding=15,
                       background=self.bg_darker,
                       foreground=self.fg_text,
                       borderwidth=1,
                       relief='flat')
        style.map('Large.TButton',
                 background=[('active', self.accent)],
                 foreground=[('active', self.fg_bright)])
        
        # Dark frame style
        style.configure('TFrame', background=self.bg_dark)
        style.configure('TLabelframe', background=self.bg_dark, 
                       foreground=self.fg_text, borderwidth=2)
        style.configure('TLabelframe.Label', background=self.bg_dark, 
                       foreground=self.fg_bright, font=self.medium_font)
        
        # New button
        ttk.Button(
            toolbar,
            text="➕ New",
            command=self.new_strategy,
            style='Large.TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        # Save button
        ttk.Button(
            toolbar,
            text="💾 Save",
            command=self.save_strategy,
            style='Large.TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        # Validate button
        ttk.Button(
            toolbar,
            text="✓ Validate",
            command=self.validate_strategy,
            style='Large.TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        # Generate button
        ttk.Button(
            toolbar,
            text="⚙ Generate",
            command=self.generate_files,
            style='Large.TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Delete button
        ttk.Button(
            toolbar,
            text="🗑 Delete",
            command=self.delete_strategy,
            style='Large.TButton'
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Refresh button
        ttk.Button(
            toolbar,
            text="🔄 Refresh",
            command=self.refresh_strategy_list,
            style='Large.TButton'
        ).pack(side=tk.LEFT, padx=2)
    
    def _create_main_layout(self):
        """Create main two-pane layout"""
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left pane: Strategy list
        left_frame = ttk.LabelFrame(main_container, text="Strategies", padding=10)
        main_container.add(left_frame, weight=1)
        
        # Search box
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_strategies())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Strategy listbox with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.strategy_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=self.medium_font,  # 32pt (4x original)
            bg=self.bg_darker,
            fg=self.fg_text,
            selectbackground=self.accent,
            selectforeground=self.fg_bright,
            highlightthickness=0,
            borderwidth=0
        )
        self.strategy_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.strategy_listbox.yview)
        
        # Bind selection event
        self.strategy_listbox.bind('<<ListboxSelect>>', self.on_strategy_select)
        self.strategy_listbox.bind('<Double-Button-1>', lambda e: self.edit_strategy())
        
        # Right pane: Editor (placeholder for now)
        right_frame = ttk.LabelFrame(main_container, text="Strategy Editor", padding=10)
        main_container.add(right_frame, weight=3)
        
        # Simple editor for MVP with dark mode
        editor_label = tk.Label(
            right_frame,
            text="📝 Strategy Editor\n\nSelect a strategy from the list to edit,\n"
                 "or click '➕ New' to create a new strategy.\n\n"
                 "Full editor coming soon!",
            justify=tk.CENTER,
            font=self.large_font,  # 40pt (4x original)
            bg=self.bg_dark,
            fg=self.fg_text
        )
        editor_label.pack(expand=True)
        
        self.editor_frame = right_frame  # Save reference for later
    
    def _create_status_bar(self):
        """Create status bar"""
        status_bar = ttk.Frame(self.root)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Dark mode status labels
        style = ttk.Style()
        style.configure('Dark.TLabel',
                       font=self.small_font,  # 28pt (4x original)
                       background=self.bg_darker,
                       foreground=self.fg_text,
                       padding=5)
        
        self.status_label = ttk.Label(
            status_bar, 
            text="Ready", 
            style='Dark.TLabel',
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.slots_label = ttk.Label(
            status_bar, 
            text="0/150 slots",
            style='Dark.TLabel'
        )
        self.slots_label.pack(side=tk.RIGHT)
        
        status_bar.configure(background=self.bg_darker)
    
    def _center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Command handlers
    
    def refresh_strategy_list(self):
        """Refresh strategy list from registry"""
        self.strategy_listbox.delete(0, tk.END)
        
        strategies = self.registry.list_strategies()
        
        for strategy in sorted(strategies, key=lambda s: s.number):
            display_text = f"{strategy.number:03d}. {strategy.name} ({strategy.category})"
            self.strategy_listbox.insert(tk.END, display_text)
        
        # Update slot count
        total = len(strategies)
        self.slots_label.config(text=f"{total}/150 slots")
        self.status_label.config(text=f"Loaded {total} strategies")
    
    def filter_strategies(self):
        """Filter strategy list based on search"""
        search_term = self.search_var.get().lower()
        
        self.strategy_listbox.delete(0, tk.END)
        strategies = self.registry.list_strategies()
        
        for strategy in sorted(strategies, key=lambda s: s.number):
            if (search_term in strategy.name.lower() or 
                search_term in strategy.category.lower() or
                search_term in str(strategy.number)):
                display_text = f"{strategy.number:03d}. {strategy.name} ({strategy.category})"
                self.strategy_listbox.insert(tk.END, display_text)
    
    def on_strategy_select(self, event):
        """Handle strategy selection"""
        selection = self.strategy_listbox.curselection()
        if selection:
            index = selection[0]
            item_text = self.strategy_listbox.get(index)
            # Extract strategy number
            strategy_num = int(item_text.split('.')[0])
            self.status_label.config(text=f"Selected: Strategy #{strategy_num:03d}")
    
    def new_strategy(self):
        """Create new strategy"""
        try:
            next_num = self.registry.get_next_strategy_number()
            messagebox.showinfo(
                "New Strategy",
                f"Creating strategy #{next_num:03d}\n\n"
                "Full editor coming in next update!\n"
                "For now, use CLI or programmatic API."
            )
        except ValueError:
            messagebox.showerror("Error", "All 150 strategy slots are filled!")
    
    def save_strategy(self):
        """Save current strategy"""
        messagebox.showinfo("Save", "Save functionality coming soon!")
    
    def validate_strategy(self):
        """Validate current strategy"""
        selection = self.strategy_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a strategy to validate")
            return
        
        index = selection[0]
        item_text = self.strategy_listbox.get(index)
        strategy_num = int(item_text.split('.')[0])
        
        config = self.registry.load_strategy(strategy_num)
        if config:
            result = self.validator.validate(config)
            if result.is_valid:
                messagebox.showinfo("Validation", "✅ Strategy is VALID!")
            else:
                errors = '\n'.join(f"• {e}" for e in result.errors)
                messagebox.showerror("Validation Failed", f"❌ Errors:\n\n{errors}")
    
    def generate_files(self):
        """Generate strategy files"""
        selection = self.strategy_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a strategy to generate")
            return
        
        index = selection[0]
        item_text = self.strategy_listbox.get(index)
        strategy_num = int(item_text.split('.')[0])
        
        try:
            files = self.registry.generate_strategy_files(strategy_num)
            if files:
                messagebox.showinfo(
                    "Success",
                    f"✅ Files generated!\n\n"
                    f"Strategy: {files['strategy']}\n"
                    f"Test: {files['test']}\n"
                    f"Config: {files['optimizer']}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Generation failed:\n{e}")
    
    def edit_strategy(self):
        """Edit selected strategy"""
        messagebox.showinfo("Edit", "Full editor coming soon!")
    
    def delete_strategy(self):
        """Delete selected strategy"""
        selection = self.strategy_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a strategy to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this strategy?"):
            # Delete functionality here
            messagebox.showinfo("Delete", "Delete functionality coming soon!")
    
    def show_statistics(self):
        """Show strategy statistics"""
        total = self.registry.get_strategy_count()
        by_category = self.registry.get_category_counts()
        
        stats_text = f"Total Strategies: {total}/150\n"
        stats_text += f"Available Slots: {150 - total}\n\n"
        stats_text += "By Category:\n"
        
        for category, count in sorted(by_category.items()):
            stats_text += f"  {category}: {count}\n"
        
        messagebox.showinfo("Statistics", stats_text)
    
    def show_help(self):
        """Show help dialog"""
        help_text = """Strategy Builder v2.0 - Quick Start

📋 Main Functions:
• Click '➕ New' to create a strategy
• Select from list to view/edit
• Click '✓ Validate' to check
• Click '⚙ Generate' to create files

⌨️ Keyboard Shortcuts:
• Ctrl+N: New strategy
• Ctrl+S: Save strategy
• Ctrl+G: Generate files
• F5: Refresh list
• Del: Delete strategy

📖 Full documentation:
docs/v3/Strategy_Builder/USER_GUIDE.md
"""
        messagebox.showinfo("Help", help_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Strategy Builder v2.0

Institutional-grade strategy creation tool
for BTC_Engine_v3.

Features:
• Visual strategy creation
• 80 production-ready building blocks
• Automated code generation
• Institutional validation

© 2026 BTC Engine Project
"""
        messagebox.showinfo("About", about_text)
    
    def quit_app(self):
        """Quit application"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            if self.owns_root:
                self.root.quit()
            else:
                self.root.destroy()
    
    def run(self):
        """Start the application"""
        if self.owns_root:
            self.root.mainloop()


def main():
    """Entry point for standalone execution"""
    app = StrategyBuilderApp()
    app.run()


if __name__ == '__main__':
    main()