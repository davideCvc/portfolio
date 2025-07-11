#!/usr/bin/env python3

import os
import sys
import json
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import webbrowser

# Modern GUI library
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
except ImportError:
    print("Please install required packages:")
    print("pip install customtkinter pillow")
    sys.exit(1)

# Import PipelineExecutor from the existing script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from pipeline_executor import PipelineExecutor
except ImportError:
    from src.pipeline.pipeline_executor import PipelineExecutor

# Configure modern theme
ctk.set_appearance_mode("dark")  # Options: "system", "dark", "light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/gui_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModernTextHandler(logging.Handler):
    """Modern handler that redirects logging output to a customtkinter Text widget"""
    
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.colors = {
            'INFO': '#00D4AA',
            'WARNING': '#FFB347', 
            'ERROR': '#FF6B6B',
            'DEBUG': '#A8E6CF'
        }
        
    def emit(self, record):
        msg = self.format(record)
        
        def append():
            try:
                self.text_widget.configure(state='normal')
                # Add timestamp with modern formatting
                timestamp = datetime.now().strftime("%H:%M:%S")
                level_color = self.colors.get(record.levelname, '#FFFFFF')
                
                # Insert with color coding
                self.text_widget.insert(tk.END, f"[{timestamp}] ", 'timestamp')
                self.text_widget.insert(tk.END, f"{record.levelname}: ", record.levelname)
                self.text_widget.insert(tk.END, f"{record.getMessage()}\n", 'message')
                
                self.text_widget.see(tk.END)
                self.text_widget.configure(state='disabled')
            except:
                pass
            
        # Schedule the update on the main thread
        self.text_widget.after(0, append)


class ModernPipelineExecutorGUI:
    def __init__(self):
        # Initialize main window with modern styling
        self.root = ctk.CTk()
        self.root.title("🚀 Pipeline Executor Pro")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Configure window
        self.setup_window()
        
        # Initialize variables
        self.region_var = tk.StringVar()
        self.category_var = tk.StringVar()
        
        # Calculate project root path
        current_file_path = os.path.abspath(__file__)
        if 'src' in current_file_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
        else:
            project_root = os.path.dirname(current_file_path)
        
        self.base_path_var = tk.StringVar(value=project_root)
        self.step_var = tk.IntVar(value=1)
        self.debug_var = tk.BooleanVar(value=False)
        self.running = False
        self.executor = None
        self.available_regions = []
        self.current_section = "dashboard"
        
        # Load data and create UI
        self.load_available_data()
        self.create_modern_ui()
        self.configure_logging()
        
        # Welcome message
        logger.info("🚀 Pipeline Executor Started")
        logger.info(f"📁 Project root: {self.base_path_var.get()}")
        
    def setup_window(self):
        """Configure window appearance and behavior"""
        # Set window icon (if available)
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "app_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
            
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def load_available_data(self):
        """Load available regions from regioni_paesi.json"""
        try:
            project_root = self.base_path_var.get()
            
            possible_paths = [
                os.path.join(project_root, "regioni_paesi.json"),
                os.path.join(project_root, "config", "regioni_paesi.json"),
                os.path.join(project_root, "scrapers", "pagine_gialle_scraper", "spiders", "regioni_paesi.json"),
                os.path.join(project_root, "src", "scrapers", "pagine_gialle_scraper", "spiders", "regioni_paesi.json")
            ]
            
            file_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    logger.info(f"✅ Found regioni_paesi.json at: {path}")
                    break
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    region_data = json.load(f)
                self.available_regions = sorted(list(region_data.keys()))
                logger.info(f"📊 Loaded {len(self.available_regions)} regions")
            else:
                self.available_regions = sorted(["emilia_romagna", "lombardia", "toscana", "veneto"])
                logger.warning("⚠️ Using default regions")
        except Exception as e:
            self.available_regions = sorted(["emilia_romagna", "lombardia", "toscana", "veneto"])
            logger.error(f"❌ Error loading regions: {e}")
    
    def create_modern_ui(self):
        """Create the modern user interface"""
        # Create main container with padding
        self.main_container = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create header
        self.create_modern_header()
        
        # Create main content area with sidebar
        self.create_content_area()
        
        # Create status bar
        self.create_modern_status_bar()
        
    def create_modern_header(self):
        """Create modern header with gradient-like effect"""
        header_frame = ctk.CTkFrame(self.main_container, height=120, corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Header content
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Left side - Logo and title
        left_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        left_frame.pack(side="left", fill="y")
        
        # Main title with modern styling
        title_label = ctk.CTkLabel(
            left_frame, 
            text="🚀 Pipeline Executor Pro", 
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=("#1f538d", "#14a085")
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            left_frame,
            text="Advanced Data Collection & Processing Platform",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="normal"),
            text_color=("gray70", "gray40")
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        # Right side - Theme toggle and info
        right_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        right_frame.pack(side="right", fill="y")
        
        # Theme toggle
        theme_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        theme_frame.pack(anchor="e")
        
        ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        
        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="Dark Mode",
            command=self.toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        self.theme_switch.pack(side="left")
        self.theme_switch.select()  # Start with dark mode
        
    def create_content_area(self):
        """Create main content area with sidebar navigation"""
        content_container = ctk.CTkFrame(self.main_container, corner_radius=15)
        content_container.pack(fill="both", expand=True)
        
        # Sidebar navigation
        self.sidebar = ctk.CTkFrame(content_container, width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=(0, 1))
        self.sidebar.pack_propagate(False)
        
        # Main content area
        self.content_frame = ctk.CTkFrame(content_container, corner_radius=0)
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        self.create_sidebar()
        self.create_main_content()
        
    def create_sidebar(self):
        """Create modern sidebar with navigation"""
        # Sidebar header
        sidebar_header = ctk.CTkFrame(self.sidebar, height=60, corner_radius=0)
        sidebar_header.pack(fill="x", padx=15, pady=(15, 10))
        sidebar_header.pack_propagate(False)
        
        nav_title = ctk.CTkLabel(
            sidebar_header,
            text="🎛️ Control Panel",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        nav_title.pack(anchor="w", pady=15)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("🏠", "Dashboard", "dashboard"),
            ("⚙️", "Configuration", "config"),
            ("📊", "Execution", "execution"),
            ("📋", "Logs", "logs"),
            ("📁", "Data Browser", "data"),
            ("❓", "Help", "help")
        ]
        
        for icon, text, key in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon} {text}",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                height=45,
                corner_radius=10,
                anchor="w",
                command=lambda k=key: self.show_section(k)
            )
            btn.pack(fill="x", padx=15, pady=5)
            self.nav_buttons[key] = btn
            
        # Spacer
        ctk.CTkFrame(self.sidebar, height=1, fg_color="transparent").pack(fill="x", expand=True)
        
        # Quick stats
        self.create_quick_stats()
        
    def create_quick_stats(self):
        """Create quick stats panel in sidebar"""
        stats_frame = ctk.CTkFrame(self.sidebar, corner_radius=10)
        stats_frame.pack(fill="x", padx=15, pady=15)
        
        stats_title = ctk.CTkLabel(
            stats_frame,
            text="📈 Quick Stats",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        stats_title.pack(pady=(15, 10))
        
        # Stats items
        self.stats_labels = {}
        stats_items = [
            ("Regions Available", len(self.available_regions)),
            ("Pipeline Status", "Ready"),
            ("Last Run", "Never")
        ]
        
        for label, value in stats_items:
            stat_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            stat_frame.pack(fill="x", padx=15, pady=2)
            
            ctk.CTkLabel(
                stat_frame,
                text=f"{label}:",
                font=ctk.CTkFont(size=11),
                text_color="gray60"
            ).pack(side="left")
            
            value_label = ctk.CTkLabel(
                stat_frame,
                text=str(value),
                font=ctk.CTkFont(size=11, weight="bold")
            )
            value_label.pack(side="right")
            self.stats_labels[label] = value_label
            
        ctk.CTkFrame(stats_frame, height=15, fg_color="transparent").pack()
        
    def create_main_content(self):
        """Create main content area with sections"""
        # Content sections
        self.sections = {}
        
        # Dashboard section
        self.sections["dashboard"] = self.create_dashboard_section()
        
        # Configuration section
        self.sections["config"] = self.create_config_section()
        
        # Execution section  
        self.sections["execution"] = self.create_execution_section()
        
        # Logs section
        self.sections["logs"] = self.create_logs_section()
        
        # Data browser section
        self.sections["data"] = self.create_data_section()
        
        # Help section
        self.sections["help"] = self.create_help_section()
        
        # Show dashboard by default
        self.show_section("dashboard")
        
    def create_dashboard_section(self):
        """Create dashboard section"""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        
        # Dashboard header
        header = ctk.CTkFrame(frame, height=60, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="🏠 Dashboard Overview",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Dashboard content
        content_scroll = ctk.CTkScrollableFrame(frame, corner_radius=10)
        content_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Welcome card
        welcome_card = ctk.CTkFrame(content_scroll, corner_radius=15)
        welcome_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            welcome_card,
            text="👋 Welcome to Pipeline Executor Pro",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        ).pack(padx=30, pady=(20, 10))
        
        ctk.CTkLabel(
            welcome_card,
            text="Your advanced data collection and processing platform. Get started by configuring your pipeline settings.",
            font=ctk.CTkFont(size=14),
            text_color="gray60",
            wraplength=800
        ).pack(padx=30, pady=(0, 20))
        
        # Quick actions
        actions_frame = ctk.CTkFrame(content_scroll, corner_radius=15)
        actions_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            actions_frame,
            text="🚀 Quick Actions",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        ).pack(padx=30, pady=(20, 15))
        
        actions_grid = ctk.CTkFrame(actions_frame, fg_color="transparent")
        actions_grid.pack(fill="x", padx=30, pady=(0, 20))
        
        # Quick action buttons
        quick_actions = [
            ("⚙️ Configure Pipeline", lambda: self.show_section("config")),
            ("▶️ Start Execution", lambda: self.show_section("execution")),
            ("📋 View Logs", lambda: self.show_section("logs")),
            ("📁 Browse Data", lambda: self.show_section("data"))
        ]
        
        for i, (text, command) in enumerate(quick_actions):
            btn = ctk.CTkButton(
                actions_grid,
                text=text,
                font=ctk.CTkFont(size=14),
                height=50,
                corner_radius=10,
                command=command
            )
            btn.grid(row=i//2, column=i%2, padx=10, pady=10, sticky="ew")
            
        actions_grid.columnconfigure(0, weight=1)
        actions_grid.columnconfigure(1, weight=1)
        
        return frame
        
    def create_config_section(self):
        """Create configuration section"""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        
        # Config header
        header = ctk.CTkFrame(frame, height=60, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="⚙️ Pipeline Configuration",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Configuration content
        config_scroll = ctk.CTkScrollableFrame(frame, corner_radius=10)
        config_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Path configuration
        path_card = ctk.CTkFrame(config_scroll, corner_radius=15)
        path_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            path_card,
            text="📁 Project Path",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        path_frame = ctk.CTkFrame(path_card, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.base_path_var,
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="📂 Browse",
            width=100,
            height=35,
            command=self.browse_path
        )
        browse_btn.pack(side="right")
        
        # Data selection
        selection_card = ctk.CTkFrame(config_scroll, corner_radius=15)
        selection_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            selection_card,
            text="🎯 Data Selection",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        selection_grid = ctk.CTkFrame(selection_card, fg_color="transparent")
        selection_grid.pack(fill="x", padx=20, pady=(0, 15))
        selection_grid.columnconfigure(1, weight=1)
        selection_grid.columnconfigure(3, weight=1)
        
        # Region selection
        ctk.CTkLabel(selection_grid, text="🗺️ Region:", font=ctk.CTkFont(size=14)).grid(
            row=0, column=0, padx=(0, 10), pady=10, sticky="w"
        )
        
        self.region_combo = ctk.CTkComboBox(
            selection_grid,
            values=self.available_regions,
            variable=self.region_var,
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.region_combo.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        if self.available_regions:
            self.region_combo.set(self.available_regions[0])
        
        # Category selection
        ctk.CTkLabel(selection_grid, text="🏪 Category:", font=ctk.CTkFont(size=14)).grid(
            row=0, column=2, padx=(0, 10), pady=10, sticky="w"
        )
        
        categories = sorted(["ristoranti", "hotel", "pizzerie", "bar", "negozi", "dentisti", "medici"])
        self.category_combo = ctk.CTkComboBox(
            selection_grid,
            values=categories,
            variable=self.category_var,
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.category_combo.grid(row=0, column=3, pady=10, sticky="ew")
        self.category_combo.set(categories[0])
        
        # Pipeline steps
        steps_card = ctk.CTkFrame(config_scroll, corner_radius=15)
        steps_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            steps_card,
            text="🔄 Pipeline Steps",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        steps_info = [
            (0, "🔄 Complete Pipeline", "Run all steps in sequence"),
            (1, "🔍 Collect Pagine Gialle", "Scrape business data from directory"),
            (2, "🧹 Normalize Business Data", "Clean and format business information"),
            (3, "⭐ Collect Google Reviews", "Scrape reviews from Google Maps"),
            (4, "📊 Normalize Review Data", "Process and analyze review data")
        ]
        
        for value, title, desc in steps_info:
            step_frame = ctk.CTkFrame(steps_card, corner_radius=10)
            step_frame.pack(fill="x", padx=20, pady=5)
            
            radio_frame = ctk.CTkFrame(step_frame, fg_color="transparent")
            radio_frame.pack(fill="x", padx=15, pady=10)
            
            radio = ctk.CTkRadioButton(
                radio_frame,
                text="",
                variable=self.step_var,
                value=value,
                font=ctk.CTkFont(size=12)
            )
            radio.pack(side="left")
            
            text_frame = ctk.CTkFrame(radio_frame, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))
            
            ctk.CTkLabel(
                text_frame,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w")
            
            ctk.CTkLabel(
                text_frame,
                text=desc,
                font=ctk.CTkFont(size=12),
                text_color="gray60"
            ).pack(anchor="w")
        
        # Debug mode
        debug_card = ctk.CTkFrame(config_scroll, corner_radius=15)
        debug_card.pack(fill="x", pady=(0, 15))
        
        debug_frame = ctk.CTkFrame(debug_card, fg_color="transparent")
        debug_frame.pack(fill="x", padx=20, pady=15)
        
        self.debug_switch = ctk.CTkSwitch(
            debug_frame,
            text="🐛 Debug Mode",
            variable=self.debug_var,
            font=ctk.CTkFont(size=14)
        )
        self.debug_switch.pack(side="left")
        self.debug_switch.configure(command=self.toggle_debug_mode)
        
        ctk.CTkLabel(
            debug_frame,
            text="Enable verbose logging for troubleshooting",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(side="left", padx=(15, 0))
        
        return frame
    
    def toggle_debug_mode(self):
        self.configure_logging()
        logger.debug("Debug mode attivato") if self.debug_var.get() else logger.info("Debug mode disattivato")

    def create_execution_section(self):
        """Create execution section"""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        
        # Execution header
        header = ctk.CTkFrame(frame, height=60, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="🚀 Pipeline Execution",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Execution content
        exec_scroll = ctk.CTkScrollableFrame(frame, corner_radius=10)
        exec_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Control panel
        control_card = ctk.CTkFrame(exec_scroll, corner_radius=15)
        control_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            control_card,
            text="🎛️ Execution Controls",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        controls_frame = ctk.CTkFrame(control_card, fg_color="transparent")
        controls_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.run_btn = ctk.CTkButton(
            controls_frame,
            text="▶️ Start Pipeline",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            width=150,
            corner_radius=10,
            command=self.run_pipeline
        )
        self.run_btn.pack(side="left", padx=(0, 10))
        
        self.stop_btn = ctk.CTkButton(
            controls_frame,
            text="⏹️ Stop",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            width=100,
            corner_radius=10,
            fg_color="gray40",
            hover_color="gray30",
            command=self.stop_pipeline,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 20))
        
        # Status display
        self.status_var = tk.StringVar(value="Ready to execute")
        status_label = ctk.CTkLabel(
            controls_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1f538d", "#14a085")
        )
        status_label.pack(side="left", padx=(20, 0))
        
        # Progress section
        progress_card = ctk.CTkFrame(exec_scroll, corner_radius=15)
        progress_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            progress_card,
            text="📊 Execution Progress",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        progress_frame = ctk.CTkFrame(progress_card, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=20,
            corner_radius=10
        )
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        # Quick info
        info_card = ctk.CTkFrame(exec_scroll, corner_radius=15)
        info_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            info_card,
            text="ℹ️ Current Configuration",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        info_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.config_info = ctk.CTkLabel(
            info_frame,
            text="Select region and category in Configuration tab",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.config_info.pack(anchor="w")
        
        return frame

    def create_logs_section(self):
        """Create logs section"""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        
        # Logs header
        header = ctk.CTkFrame(frame, height=60, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=20, pady=15)
        
        ctk.CTkLabel(
            header_content,
            text="📋 Execution Logs",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        ).pack(side="left")
        
        # Log controls
        controls_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        controls_frame.pack(side="right")
        
        clear_btn = ctk.CTkButton(
            controls_frame,
            text="🗑️ Clear",
            width=80,
            height=30,
            command=self.clear_logs
        )
        clear_btn.pack(side="right", padx=(0, 10))
        
        save_btn = ctk.CTkButton(
            controls_frame,
            text="💾 Save",
            width=80,
            height=30,
            command=self.save_logs
        )
        save_btn.pack(side="right")
        
        # Logs content
        logs_frame = ctk.CTkFrame(frame, corner_radius=10)
        logs_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create text widget for logs
        self.log_text = ctk.CTkTextbox(
            logs_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=0,
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=15)
        
        return frame
        
    def create_data_section(self):
        """Create data browser section"""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        
        # Data header
        header = ctk.CTkFrame(frame, height=60, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="📁 Data Browser",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Data content
        data_scroll = ctk.CTkScrollableFrame(frame, corner_radius=10)
        data_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Output directories
        dirs_card = ctk.CTkFrame(data_scroll, corner_radius=15)
        dirs_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            dirs_card,
            text="📂 Output Directories",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        # Directory buttons
        dirs_frame = ctk.CTkFrame(dirs_card, fg_color="transparent")
        dirs_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        dir_buttons = [
            ("📄 Raw Data", "data/raw"),
            ("🧹 Processed Data", "data/processed_data"),
            ("📊 Final Output", "data/processed_data/clean_post_google_reviews"),
            ("📋 Logs", "logs")
        ]
        
        for i, (text, path) in enumerate(dir_buttons):
            btn = ctk.CTkButton(
                dirs_frame,
                text=text,
                height=40,
                corner_radius=8,
                command=lambda p=path: self.open_directory(p)
            )
            btn.grid(row=i//2, column=i%2, padx=10, pady=5, sticky="ew")
            
        dirs_frame.columnconfigure(0, weight=1)
        dirs_frame.columnconfigure(1, weight=1)
        
        # Recent files
        files_card = ctk.CTkFrame(data_scroll, corner_radius=15)
        files_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            files_card,
            text="📋 Recent Files",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        # File list
        self.file_list_frame = ctk.CTkFrame(files_card, fg_color="transparent")
        self.file_list_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        # Populate file list
        self.refresh_file_list()
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            files_card,
            text="🔄 Refresh",
            height=35,
            command=self.refresh_file_list
        )
        refresh_btn.pack(padx=20, pady=(0, 15))
        
        return frame
        
    def create_help_section(self):
        """Create help section"""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=0, fg_color="transparent")
        
        # Help header
        header = ctk.CTkFrame(frame, height=60, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="❓ Help & Documentation",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Help content
        help_scroll = ctk.CTkScrollableFrame(frame, corner_radius=10)
        help_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Getting started
        start_card = ctk.CTkFrame(help_scroll, corner_radius=15)
        start_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            start_card,
            text="🚀 Getting Started",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        start_text = """
1. Configure your project path in the Configuration section
2. Select the region and category you want to scrape
3. Choose the pipeline step to execute
4. Click 'Start Pipeline' in the Execution section
5. Monitor progress in the Logs section
        """
        
        ctk.CTkLabel(
            start_card,
            text=start_text.strip(),
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            justify="left"
        ).pack(padx=20, pady=(0, 15), anchor="w")
        
        # Pipeline steps
        steps_card = ctk.CTkFrame(help_scroll, corner_radius=15)
        steps_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            steps_card,
            text="🔄 Pipeline Steps Explained",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        steps_text = """
• Complete Pipeline: Runs all steps sequentially
• Collect Pagine Gialle: Scrapes business listings from directory
• Normalize Business Data: Cleans and formats business information
• Collect Google Reviews: Scrapes reviews from Google Maps
• Normalize Review Data: Processes and analyzes review data
        """
        
        ctk.CTkLabel(
            steps_card,
            text=steps_text.strip(),
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            justify="left"
        ).pack(padx=20, pady=(0, 15), anchor="w")
        
        # Troubleshooting
        trouble_card = ctk.CTkFrame(help_scroll, corner_radius=15)
        trouble_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            trouble_card,
            text="🔧 Troubleshooting",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        trouble_text = """
• Enable Debug Mode for detailed logging
• Check the Logs section for error messages
• Ensure all required files are in the project directory
• Verify internet connection for web scraping
• Check file permissions for output directories
        """
        
        ctk.CTkLabel(
            trouble_card,
            text=trouble_text.strip(),
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            justify="left"
        ).pack(padx=20, pady=(0, 15), anchor="w")
        
        # Links
        links_card = ctk.CTkFrame(help_scroll, corner_radius=15)
        links_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            links_card,
            text="🔗 Useful Links",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        links_frame = ctk.CTkFrame(links_card, fg_color="transparent")
        links_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        link_buttons = [
            ("📖 Documentation", "https://github.com"),
            ("🐛 Report Bug", "https://github.com/issues"),
            ("💡 Feature Request", "https://github.com/issues"),
            ("📧 Contact Support", "mailto:support@example.com")
        ]
        
        for text, url in link_buttons:
            btn = ctk.CTkButton(
                links_frame,
                text=text,
                height=35,
                corner_radius=8,
                command=lambda u=url: webbrowser.open(u)
            )
            btn.pack(fill="x", pady=2)
        
        return frame
        
    def create_modern_status_bar(self):
        """Create modern status bar"""
        self.status_bar = ctk.CTkFrame(self.main_container, height=40, corner_radius=10)
        self.status_bar.pack(fill="x", pady=(10, 0))
        self.status_bar.pack_propagate(False)
        
        status_content = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        status_content.pack(fill="both", expand=True, padx=20, pady=8)
        
        # Status text
        self.status_text = ctk.CTkLabel(
            status_content,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.status_text.pack(side="left")
        
        # Time display
        self.time_label = ctk.CTkLabel(
            status_content,
            text=datetime.now().strftime("%H:%M:%S"),
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.time_label.pack(side="right")
        
        # Update time every second
        self.update_time()
        
    def show_section(self, section_name):
        """Show specific section and update navigation"""
        # Hide all sections
        for name, section in self.sections.items():
            section.pack_forget()
            
        # Update button states
        for name, button in self.nav_buttons.items():
            if name == section_name:
                button.configure(fg_color=("#3B8ED0", "#1F6AA5"))
            else:
                button.configure(fg_color=("gray75", "gray25"))
                
        # Show selected section
        if section_name in self.sections:
            self.sections[section_name].pack(fill="both", expand=True)
            self.current_section = section_name
            
        # Update config info in execution section
        if section_name == "execution":
            self.update_config_info()
            
    def update_config_info(self):
        """Update configuration info display"""
        region = self.region_var.get() or "Not selected"
        category = self.category_var.get() or "Not selected"
        step = self.step_var.get()
        
        step_names = {
            0: "Complete Pipeline",
            1: "Collect Pagine Gialle",
            2: "Normalize Business Data", 
            3: "Collect Google Reviews",
            4: "Normalize Review Data"
        }
        
        step_name = step_names.get(step, "Unknown")
        
        info_text = f"Region: {region} | Category: {category} | Step: {step_name}"
        if hasattr(self, 'config_info'):
            self.config_info.configure(text=info_text)
            
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self.theme_switch.get():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
            
    def browse_path(self):
        """Browse for project path"""
        path = filedialog.askdirectory(title="Select Project Root Directory")
        if path:
            self.base_path_var.set(path)
            self.load_available_data()
            logger.info(f"📁 Project path updated: {path}")
            
    def configure_logging(self):
        """Configure logging to redirect to GUI"""
        if hasattr(self, 'log_text'):
            self.gui_handler = ModernTextHandler(self.log_text)

            if self.debug_var.get():
                self.gui_handler.setLevel(logging.DEBUG)
                logger.setLevel(logging.DEBUG)
            else:
                self.gui_handler.setLevel(logging.INFO)
                logger.setLevel(logging.INFO)

            logger.addHandler(self.gui_handler)
            
    def clear_logs(self):
        """Clear the log display"""
        if hasattr(self, 'log_text'):
            self.log_text.delete("1.0", tk.END)
            
    def save_logs(self):
        """Save logs to file"""
        if hasattr(self, 'log_text'):
            content = self.log_text.get("1.0", tk.END)
            filename = f"logs/gui_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            
            try:
                os.makedirs("logs", exist_ok=True)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Logs saved to {filename}")
                logger.info(f"💾 Logs saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")
                logger.error(f"❌ Failed to save logs: {e}")
                
    def open_directory(self, path):
        """Open directory in file explorer"""
        full_path = os.path.join(self.base_path_var.get(), path)
        
        if not os.path.exists(full_path):
            os.makedirs(full_path, exist_ok=True)
            
        try:
            if sys.platform == "win32":
                os.startfile(full_path)
            elif sys.platform == "darwin":
                os.system(f"open '{full_path}'")
            else:
                os.system(f"xdg-open '{full_path}'")
            logger.info(f"📂 Opened directory: {full_path}")
        except Exception as e:
            logger.error(f"❌ Failed to open directory: {e}")
            messagebox.showerror("Error", f"Failed to open directory: {e}")
            
    def refresh_file_list(self):
        """Refresh the recent files list"""
        # Clear existing widgets
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
            
        try:
            project_root = self.base_path_var.get()
            recent_files = []
            
            # Check for recent output files
            output_dirs = ["data/output", "data/processed", "logs"]
            
            for dir_name in output_dirs:
                dir_path = os.path.join(project_root, dir_name)
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        if file.endswith(('.csv', '.json', '.log')):
                            file_path = os.path.join(dir_path, file)
                            mtime = os.path.getmtime(file_path)
                            recent_files.append((file_path, mtime, file))
                            
            # Sort by modification time
            recent_files.sort(key=lambda x: x[1], reverse=True)
            recent_files = recent_files[:10]  # Show last 10 files
            
            if recent_files:
                for i, (file_path, mtime, filename) in enumerate(recent_files):
                    file_frame = ctk.CTkFrame(self.file_list_frame, corner_radius=5)
                    file_frame.pack(fill="x", pady=2)
                    
                    # File info
                    info_frame = ctk.CTkFrame(file_frame, fg_color="transparent")
                    info_frame.pack(fill="x", padx=10, pady=5)
                    
                    # Filename
                    ctk.CTkLabel(
                        info_frame,
                        text=filename,
                        font=ctk.CTkFont(size=12, weight="bold")
                    ).pack(side="left")
                    
                    # Modified time
                    mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    ctk.CTkLabel(
                        info_frame,
                        text=mod_time,
                        font=ctk.CTkFont(size=10),
                        text_color="gray60"
                    ).pack(side="right")
                    
                    # Open button
                    open_btn = ctk.CTkButton(
                        info_frame,
                        text="📂",
                        width=30,
                        height=25,
                        command=lambda fp=file_path: self.open_file(fp)
                    )
                    open_btn.pack(side="right", padx=(5, 0))
            else:
                ctk.CTkLabel(
                    self.file_list_frame,
                    text="No recent files found",
                    font=ctk.CTkFont(size=12),
                    text_color="gray60"
                ).pack(pady=10)
                
        except Exception as e:
            logger.error(f"❌ Error refreshing file list: {e}")
            ctk.CTkLabel(
                self.file_list_frame,
                text="Error loading files",
                font=ctk.CTkFont(size=12),
                text_color="red"
            ).pack(pady=10)
            
    def open_file(self, file_path):
        """Open file with default application"""
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                os.system(f"open '{file_path}'")
            else:
                os.system(f"xdg-open '{file_path}'")
            logger.info(f"📄 Opened file: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to open file: {e}")
            messagebox.showerror("Error", f"Failed to open file: {e}")
            
    def update_time(self):
        """Update time display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        self.root.after(1000, self.update_time)
        
    def run_pipeline(self):
        """Run the pipeline in a separate thread"""
        if self.running:
            return
        
        # Validate step input - FIXED: Allow step 0 (Complete Pipeline)
        try:
            step_value = self.step_var.get()
            if not isinstance(step_value, int) or step_value < 0 or step_value > 4:
                messagebox.showerror("Error", "Step deve essere tra 0 e 4")
                return
        except tk.TclError:
            messagebox.showerror("Error", "Step deve essere un numero valido tra 0 e 4")
            return
            
        # Validate inputs
        if not self.region_var.get():
            messagebox.showerror("Error", "Please select a region")
            return
            
        if not self.category_var.get():
            messagebox.showerror("Error", "Please select a category")
            return
            
        # Update UI state
        self.running = True
        self.run_btn.configure(state="disabled", text="🔄 Running...")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_var.set("Pipeline running...")
        
        # Update stats
        self.stats_labels["Pipeline Status"].configure(text="Running")
        self.stats_labels["Last Run"].configure(text=datetime.now().strftime("%H:%M:%S"))
        
        # Start pipeline thread
        self.pipeline_thread = threading.Thread(target=self._run_pipeline_thread, daemon=True)
        self.pipeline_thread.start()
        
        logger.info("🚀 Pipeline execution started")
        
    def _run_pipeline_thread(self):
        """Pipeline execution in separate thread"""
        try:
            # Create executor
            self.executor = PipelineExecutor(
                base_path=self.base_path_var.get(),
                debug=self.debug_var.get(),
                region=self.region_var.get(),
                category=self.category_var.get()
            )

            # Set up progress callback
            def progress_callback(step, total):
                progress = step / total if total > 0 else 0
                self.root.after(0, lambda: self.progress_bar.set(progress))

            # Decidi se eseguire tutta la pipeline o uno step singolo
            step = self.step_var.get()
            if step == 0:
                success = self.executor.run_full_pipeline(progress_callback=progress_callback)
            else:
                success = self.executor.run_step(
                    region=self.region_var.get(),
                    category=self.category_var.get(),
                    step=step,
                    progress_callback=progress_callback
                )

            # Update UI on completion
            def on_complete():
                self.running = False
                self.run_btn.configure(state="normal", text="▶️ Start Pipeline")
                self.stop_btn.configure(state="disabled")
                self.progress_bar.set(1.0 if success else 0)

                if success:
                    self.status_var.set("Pipeline completed successfully")
                    self.stats_labels["Pipeline Status"].configure(text="Completed")
                    logger.info("✅ Pipeline execution completed successfully")
                else:
                    self.status_var.set("Pipeline failed")
                    self.stats_labels["Pipeline Status"].configure(text="Failed")
                    logger.error("❌ Pipeline execution failed")

                self.refresh_file_list()

            self.root.after(0, on_complete)

        except Exception as e:
            logger.error(f"❌ Pipeline execution error: {e}")

            def on_error():
                self.running = False
                self.run_btn.configure(state="normal", text="▶️ Start Pipeline")
                self.stop_btn.configure(state="disabled")
                self.progress_bar.set(0)
                self.status_var.set("Pipeline error")
                self.stats_labels["Pipeline Status"].configure(text="Error")

            self.root.after(0, on_error)

            
    def stop_pipeline(self):
        """Stop the running pipeline"""
        if not self.running:
            return
            
        try:
            if self.executor and hasattr(self.executor, 'stop'):
                self.executor.stop()
                
            self.running = False
            self.run_btn.configure(state="normal", text="▶️ Start Pipeline")
            self.stop_btn.configure(state="disabled")
            self.progress_bar.set(0)
            self.status_var.set("Pipeline stopped")
            self.stats_labels["Pipeline Status"].configure(text="Stopped")
            
            logger.info("⏹️ Pipeline execution stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping pipeline: {e}")
            
    def run(self):
        """Start the GUI application"""
        try:
            logger.info("🚀 Starting Pipeline Executor GUI")
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("👋 Application interrupted by user")
        except Exception as e:
            logger.error(f"❌ Application error: {e}")
        finally:
            logger.info("👋 Pipeline Executor GUI closed")


def main():
    """Main entry point"""
    try:
        app = ModernPipelineExecutorGUI()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)

import logging
import sys

# Handler personalizzato che forza la codifica UTF-8
class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        if stream is None:
            stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        super().__init__(stream)

# Configura il logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Rimuovi gli handler esistenti
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Aggiungi l'handler UTF-8
handler = UTF8StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":
    main()