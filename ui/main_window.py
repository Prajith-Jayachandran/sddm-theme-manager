"""
SDDM Theme Manager - Main Application Window
Coordinates toolbar, theme grid, details panel, status bar, and actions.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.background import BackgroundManager
from core.installer import ThemeInstaller
from core.polkit import detect_sddm_qt_version, is_sddm_installed
from core.preview import PreviewManager
from core.theme_applier import ThemeApplier
from core.theme_scanner import Theme, ThemeScanner
from ui.detail_panel import DetailPanel
from ui.preview_overlay import PreviewExitOverlay
from ui.store_dialog import StoreDialog
from ui.theme_grid import ThemeGridWidget


class MainWindow(QMainWindow):
    """Main Application Window for SDDM Theme Manager."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDDM Theme Manager")
        self.resize(960, 640)
        self.setMinimumSize(780, 520)

        self.preview_manager = PreviewManager()
        self.preview_manager.preview_started.connect(self._on_preview_started)
        self.preview_manager.preview_stopped.connect(self._on_preview_stopped)
        self.preview_manager.preview_error.connect(self._on_preview_error)

        self.preview_overlay = PreviewExitOverlay()
        self.preview_overlay.exit_requested.connect(self._on_overlay_exit_requested)

        self.shortcut_esc_preview = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc_preview.activated.connect(self._on_esc_pressed)

        self.current_selected_theme: Optional[Theme] = None
        self._init_ui()
        self.refresh_themes()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_vlayout = QVBoxLayout(central_widget)
        self.main_vlayout.setContentsMargins(0, 0, 0, 0)
        self.main_vlayout.setSpacing(0)

        # 1. Main Splitter (Left: Grid, Right: Detail Panel)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(2)

        self.theme_grid = ThemeGridWidget(self)
        self.theme_grid.theme_selected.connect(self._on_theme_selected)
        self.theme_grid.theme_double_clicked.connect(self._on_theme_double_clicked)
        self.theme_grid.apply_requested.connect(self.apply_theme)
        self.theme_grid.sync_requested.connect(self.sync_theme)
        self.theme_grid.preview_requested.connect(self.toggle_preview)
        self.theme_grid.set_background_requested.connect(self.set_theme_background)
        self.theme_grid.reset_background_requested.connect(self.reset_theme_background)
        self.theme_grid.remove_requested.connect(self.remove_theme)
        self.theme_grid.open_folder_requested.connect(self.open_theme_folder)

        self.detail_panel = DetailPanel(self)
        self.detail_panel.preview_clicked.connect(self.toggle_preview)
        self.detail_panel.apply_clicked.connect(self.apply_theme)
        self.detail_panel.sync_clicked.connect(self.sync_theme)
        self.detail_panel.set_background_clicked.connect(self.set_theme_background)
        self.detail_panel.reset_background_clicked.connect(self.reset_theme_background)
        self.detail_panel.remove_clicked.connect(self.remove_theme)
        self.detail_panel.open_folder_clicked.connect(self.open_theme_folder)

        self.splitter.addWidget(self.theme_grid)
        self.splitter.addWidget(self.detail_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        # 2. SDDM Missing Warning Banner
        self._setup_warning_banner()

        # 3. Top Toolbar
        self._setup_toolbar()

        self.main_vlayout.addWidget(self.splitter, 1)

        # 4. Status Bar
        self._setup_statusbar()

    def _setup_warning_banner(self):
        # 1. SDDM Missing Warning Banner
        if not is_sddm_installed():
            self.warning_frame = QFrame()
            self.warning_frame.setObjectName("warningBanner")
            layout = QHBoxLayout(self.warning_frame)
            layout.setContentsMargins(12, 6, 12, 6)

            warn_lbl = QLabel(
                "⚠️ SDDM does not appear to be installed on this system. "
                "Themes can still be inspected, but applying or previewing requires SDDM."
            )
            warn_lbl.setObjectName("warningText")
            layout.addWidget(warn_lbl)
            self.main_vlayout.addWidget(self.warning_frame)

        # 2. Live Preview Running Banner (top of window)
        self.preview_active_frame = QFrame()
        self.preview_active_frame.setStyleSheet(
            "QFrame { background-color: #f7768e; border-bottom: 2px solid #db4b4b; padding: 4px; }"
        )
        p_layout = QHBoxLayout(self.preview_active_frame)
        p_layout.setContentsMargins(16, 6, 16, 6)
        self.lbl_preview_banner_text = QLabel("● SDDM Live Preview is currently RUNNING fullscreen on your display")
        self.lbl_preview_banner_text.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        p_layout.addWidget(self.lbl_preview_banner_text)
        p_layout.addStretch()

        btn_stop = QPushButton("✕ Stop Live Preview (Esc)")
        btn_stop.setCursor(Qt.PointingHandCursor)
        btn_stop.setStyleSheet(
            "QPushButton { background-color: #1a1b26; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #24283b; }"
        )
        btn_stop.clicked.connect(self._on_overlay_exit_requested)
        p_layout.addWidget(btn_stop)
        self.preview_active_frame.setVisible(False)
        self.main_vlayout.addWidget(self.preview_active_frame)

        # 3. Active Theme Health Warning Banner (e.g. active in config but missing from /usr/share/sddm/themes/)
        self.health_warning_frame = QFrame()
        self.health_warning_frame.setStyleSheet(
            "QFrame { background-color: #3b3220; border-bottom: 2px solid #e0af68; padding: 6px; }"
        )
        h_layout = QHBoxLayout(self.health_warning_frame)
        h_layout.setContentsMargins(16, 6, 16, 6)
        self.lbl_health_warning = QLabel()
        self.lbl_health_warning.setStyleSheet("color: #e0af68; font-weight: 600; font-size: 12px;")
        self.lbl_health_warning.setWordWrap(True)
        h_layout.addWidget(self.lbl_health_warning, 1)

        self.btn_fix_health = QPushButton("⚡ Fix & Sync to SDDM Now")
        self.btn_fix_health.setCursor(Qt.PointingHandCursor)
        self.btn_fix_health.setStyleSheet(
            "QPushButton { background-color: #e0af68; color: #1a1b26; font-weight: bold; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #ff9e3b; }"
        )
        self.btn_fix_health.clicked.connect(self.fix_active_theme)
        h_layout.addWidget(self.btn_fix_health)
        self.health_warning_frame.setVisible(False)
        self.main_vlayout.addWidget(self.health_warning_frame)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Action: Install from file
        btn_install = QPushButton(" Install from File…")
        btn_install.setCursor(Qt.PointingHandCursor)
        btn_install.clicked.connect(self.install_from_file)
        toolbar.addWidget(btn_install)

        # Action: Get New Themes
        btn_store = QPushButton(" Get New Themes")
        btn_store.setCursor(Qt.PointingHandCursor)
        btn_store.clicked.connect(self.open_store_dialog)
        toolbar.addWidget(btn_store)

        # Action: Sync All Themes to SDDM System
        btn_sync_all = QPushButton(" ⟳ Sync to SDDM")
        btn_sync_all.setToolTip("Sync all user-installed themes to /usr/share/sddm/themes/")
        btn_sync_all.setCursor(Qt.PointingHandCursor)
        btn_sync_all.clicked.connect(self.sync_all_themes)
        toolbar.addWidget(btn_sync_all)

        # Action: Refresh
        btn_refresh = QPushButton(" Refresh")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_themes)
        toolbar.addWidget(btn_refresh)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # Qt Version Filter
        lbl_qt = QLabel(" Filter: ")
        lbl_qt.setStyleSheet("color: #787c99; font-weight: 500;")
        toolbar.addWidget(lbl_qt)

        self.combo_qt = QComboBox()
        self.combo_qt.addItems(["All", "Qt 6", "Qt 5"])
        self.combo_qt.currentTextChanged.connect(self.theme_grid.set_qt_filter)
        toolbar.addWidget(self.combo_qt)

        # Sort Dropdown
        lbl_sort = QLabel("  Sort: ")
        lbl_sort.setStyleSheet("color: #787c99; font-weight: 500;")
        toolbar.addWidget(lbl_sort)

        self.combo_sort = QComboBox()
        self.combo_sort.addItems([
            "Name (A-Z)",
            "Name (Z-A)",
            "Installation Date (Newest)",
            "Installation Date (Oldest)",
        ])
        self.combo_sort.currentTextChanged.connect(self.theme_grid.set_sort_order)
        toolbar.addWidget(self.combo_sort)

        # Search Input
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search themes…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self.theme_grid.set_search_query)
        toolbar.addWidget(self.search_box)

    def _setup_statusbar(self):
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self.lbl_status_active = QLabel("Active Theme: None")
        self.lbl_status_active.setStyleSheet("color: #10b981; font-weight: 600; padding-right: 15px;")
        status_bar.addWidget(self.lbl_status_active)

        qt_desc, _ = detect_sddm_qt_version()
        self.lbl_status_greeter = QLabel(f"SDDM Greeter: {qt_desc}")
        self.lbl_status_greeter.setStyleSheet("color: #7aa2f7; padding-right: 15px;")
        status_bar.addWidget(self.lbl_status_greeter)

        self.lbl_status_count = QLabel("0 themes")
        self.lbl_status_count.setStyleSheet("color: #9aa5ce;")
        status_bar.addPermanentWidget(self.lbl_status_count)

    def refresh_themes(self, select_path: Optional[Path] = None):
        """Scans directories, updates UI list, and updates status bar."""
        themes = ThemeScanner.scan_themes()
        active_name = ThemeScanner.get_active_theme_name()

        self.lbl_status_active.setText(f"Active Theme: {active_name or 'None'}")
        self.lbl_status_count.setText(f"{len(themes)} themes found")

        # Health verification of configured active theme
        is_healthy, health_msg, act_id = ThemeApplier.check_active_theme_health()
        if not is_healthy and act_id:
            self.lbl_health_warning.setText(
                f"⚠️ Active SDDM theme '{act_id}' is missing from system directory (/usr/share/sddm/themes/)!\n"
                "SDDM will fall back to default until synced."
            )
            self.health_warning_frame.setVisible(True)
        else:
            self.health_warning_frame.setVisible(False)

        self.theme_grid.set_themes(themes)

        # Reselect theme
        target_theme = None
        if select_path:
            for t in themes:
                if t.path == select_path or t.id == select_path.name:
                    target_theme = t
                    break
        elif self.current_selected_theme:
            for t in themes:
                if t.path == self.current_selected_theme.path:
                    target_theme = t
                    break

        if not target_theme and themes:
            for t in themes:
                if t.is_active:
                    target_theme = t
                    break
            if not target_theme:
                target_theme = themes[0]

        if target_theme:
            self.theme_grid.select_theme(target_theme)
        else:
            self.detail_panel.set_theme(None)

    def _on_theme_selected(self, theme: Theme):
        self.current_selected_theme = theme
        self.detail_panel.set_theme(theme)

    def _on_theme_double_clicked(self, theme: Theme):
        self.toggle_preview(theme)

    def _on_esc_pressed(self):
        """Escape shortcut handler: stops preview if running."""
        if self.preview_manager.is_running():
            self._on_overlay_exit_requested()

    def toggle_preview(self, theme: Theme):
        """Starts or terminates live greeter test mode preview."""
        if self.preview_manager.is_running():
            self.preview_manager.stop_preview()
            self.detail_panel.set_preview_running(False)
            self.preview_active_frame.setVisible(False)
            self.statusBar().showMessage("Preview closed.", 3000)
        else:
            self.statusBar().showMessage(f"Launching live preview for '{theme.name}'…")
            ok, msg = self.preview_manager.start_preview(theme.path, theme.qt_version)
            if not ok:
                QMessageBox.critical(self, "Preview Error", f"Could not launch SDDM preview:\n\n{msg}")

    def _on_preview_started(self, theme_path: str):
        self.detail_panel.set_preview_running(True)
        theme_name = Path(theme_path).name
        self.lbl_preview_banner_text.setText(f"● Live SDDM Preview is RUNNING for '{theme_name}' (Fullscreen)")
        self.preview_active_frame.setVisible(True)

        # Ensure top overlay appears on top of newly spawned greeter window
        QTimer.singleShot(400, self.preview_overlay.show_top_center)
        QTimer.singleShot(1200, self.preview_overlay.show_top_center)
        self.statusBar().showMessage(f"Live preview running for: {theme_name} — Press Esc or click 'Exit Preview' to stop")

    def _on_preview_stopped(self, returncode: int, stderr_msg: str):
        self.preview_overlay.hide()
        self.preview_active_frame.setVisible(False)
        self.detail_panel.set_preview_running(False)
        self.statusBar().showMessage("Live preview finished.", 3000)

    def _on_preview_error(self, err_msg: str):
        self.preview_overlay.hide()
        self.preview_active_frame.setVisible(False)
        self.detail_panel.set_preview_running(False)
        QMessageBox.critical(self, "Preview Error", err_msg)

    def _on_overlay_exit_requested(self):
        self.preview_overlay.hide()
        self.preview_active_frame.setVisible(False)
        if self.preview_manager.is_running():
            self.preview_manager.stop_preview()
        self.detail_panel.set_preview_running(False)
        self.statusBar().showMessage("Preview closed.", 3000)

    def sync_theme(self, theme: Theme):
        """Copies the specified theme to /usr/share/sddm/themes/."""
        self.statusBar().showMessage(f"Syncing '{theme.name}' to SDDM system folder…")
        ok, msg = ThemeApplier.sync_theme_to_system(theme.path, theme.id)
        if ok:
            QMessageBox.information(
                self,
                "Theme Synced",
                f"Theme '{theme.name}' was successfully synced to /usr/share/sddm/themes/{theme.id}!\n\n"
                "SDDM daemon can now display this theme on boot and login.",
            )
            self.refresh_themes(select_path=theme.path)
        else:
            QMessageBox.critical(self, "Sync Failed", f"Could not sync theme to system directory:\n\n{msg}")

    def sync_all_themes(self):
        """Synchronizes all user themes to /usr/share/sddm/themes/."""
        self.statusBar().showMessage("Syncing all user themes to /usr/share/sddm/themes/…")
        ok_count, err_count, msgs = ThemeApplier.sync_all_user_themes()
        msg_text = "\n".join(msgs)
        if err_count == 0 and ok_count > 0:
            QMessageBox.information(
                self,
                "Sync Complete",
                f"Successfully synced {ok_count} theme(s) to /usr/share/sddm/themes/:\n\n{msg_text}",
            )
        elif ok_count > 0:
            QMessageBox.warning(
                self,
                "Sync Partially Completed",
                f"Synced {ok_count} theme(s) with {err_count} failure(s):\n\n{msg_text}",
            )
        elif err_count > 0:
            QMessageBox.critical(self, "Sync Failed", f"Failed to sync themes:\n\n{msg_text}")
        else:
            QMessageBox.information(self, "Sync Complete", "All user themes are already synchronized to SDDM.")
        self.refresh_themes()

    def fix_active_theme(self):
        """Locates and syncs the currently configured active theme."""
        active_name = ThemeScanner.get_active_theme_name()
        if not active_name:
            return
        user_theme = Path.home() / ".local/share/sddm/themes" / active_name
        if user_theme.exists():
            ok, msg = ThemeApplier.sync_theme_to_system(user_theme, active_name)
            if ok:
                QMessageBox.information(
                    self,
                    "Active Theme Repaired",
                    f"Successfully installed active theme '{active_name}' into /usr/share/sddm/themes/!\n\n"
                    "SDDM will now load this theme properly.",
                )
                self.refresh_themes(select_path=user_theme)
            else:
                QMessageBox.critical(self, "Repair Failed", f"Failed to sync active theme:\n\n{msg}")
        else:
            QMessageBox.warning(
                self,
                "Theme Not Found",
                f"Theme directory for '{active_name}' was not found in ~/.local/share/sddm/themes/.",
            )

    def apply_theme(self, theme: Theme):
        """Writes /etc/sddm.conf.d/10-theme.conf and optionally restarts SDDM."""
        ok, msg = ThemeApplier.apply_theme(theme)
        if not ok:
            err_details = msg
            if "Not authorized" in msg:
                err_details += (
                    "\n\n💡 Polkit authorization failed. Update the rule file with:\n"
                    "  sudo cp ~/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/\n"
                    "  sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules\n"
                    "  sudo systemctl restart polkit\n\n"
                    "Alternatively, run the app with --no-polkit."
                )
            QMessageBox.critical(self, "Failed to Apply Theme", f"Could not apply theme:\n\n{err_details}")
            return

        # Success: refresh list so active badges update
        self.refresh_themes(select_path=theme.path)

        # Prompt for SDDM restart
        reply = QMessageBox.question(
            self,
            "Theme Applied",
            f"SDDM theme successfully set to '{theme.name}'!\n\n"
            "Would you like to restart the SDDM service now to view changes?\n\n"
            "⚠️ Warning: Your current session will be restarted. Save all open work!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.statusBar().showMessage("Restarting SDDM service…")
            restart_ok, restart_msg = ThemeApplier.restart_sddm()
            if not restart_ok:
                QMessageBox.warning(self, "Restart Failed", f"Failed to restart SDDM:\n\n{restart_msg}")

    def set_theme_background(self, theme: Theme):
        """Opens file picker and writes theme.conf.user."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Background Image for '{theme.name}'",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.webp *.svg *.bmp);;All Files (*)",
        )
        if not file_path:
            return

        ok, msg = BackgroundManager.set_background(theme.path, file_path)
        if ok:
            QMessageBox.information(self, "Background Set", f"Background successfully updated for '{theme.name}'!")
            self.refresh_themes(select_path=theme.path)
        else:
            QMessageBox.critical(self, "Failed to Set Background", f"Error updating background:\n\n{msg}")

    def reset_theme_background(self, theme: Theme):
        """Resets theme background to default."""
        reply = QMessageBox.question(
            self,
            "Reset Background",
            f"Reset custom background for '{theme.name}' to default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = BackgroundManager.reset_background(theme.path)
        if ok:
            QMessageBox.information(self, "Background Reset", msg)
            self.refresh_themes(select_path=theme.path)
        else:
            QMessageBox.critical(self, "Failed to Reset Background", f"Error resetting background:\n\n{msg}")

    def install_from_file(self):
        """Installs theme archive (.tar.gz, .zip, etc.) into user directory."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SDDM Theme Archive",
            str(Path.home()),
            "Theme Archives (*.tar.gz *.tgz *.tar.xz *.tar.bz2 *.tar *.zip);;All Files (*)",
        )
        if not file_path:
            return

        ok, installed_path, msg = ThemeInstaller.install_from_archive(file_path)
        if ok and installed_path:
            # Sync to system path with elevated privileges so SDDM can immediately load it
            sync_ok, sync_msg = ThemeApplier.sync_theme_to_system(installed_path, installed_path.name)
            if sync_ok:
                msg += f"\n\n✓ Synchronized to SDDM system folder: /usr/share/sddm/themes/{installed_path.name}"
            QMessageBox.information(self, "Theme Installed", msg)
            self.refresh_themes(select_path=installed_path)
        else:
            QMessageBox.critical(self, "Installation Failed", f"Could not install theme:\n\n{msg}")

    def open_store_dialog(self):
        """Opens KDE Store dialog for online themes."""
        dlg = StoreDialog(self)
        dlg.theme_installed.connect(self.refresh_themes)
        dlg.exec()

    def remove_theme(self, theme: Theme):
        """Confirms and removes a theme."""
        warning_extra = ""
        if theme.is_active:
            warning_extra += "\n\n⚠️ WARNING: This theme is currently active in SDDM!"
        if theme.is_system:
            warning_extra += "\n\nNote: This is a system-level theme and requires administrator authentication."

        reply = QMessageBox.question(
            self,
            "Remove Theme",
            f"Are you sure you want to permanently remove '{theme.name}'?{warning_extra}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = ThemeInstaller.remove_theme(theme.path)
        if ok:
            QMessageBox.information(self, "Theme Removed", msg)
            self.refresh_themes()
        else:
            QMessageBox.critical(self, "Removal Failed", f"Could not remove theme:\n\n{msg}")

    def open_theme_folder(self, theme: Theme):
        """Opens theme folder in default file manager."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(theme.path)))

    def closeEvent(self, event):
        """Ensure preview process is cleanly terminated on window close."""
        self.preview_overlay.hide()
        if self.preview_manager.is_running():
            self.preview_manager.stop_preview()
        event.accept()
