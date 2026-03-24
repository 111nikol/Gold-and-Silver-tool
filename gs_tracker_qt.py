#!/usr/bin/env python3
"""Modern Qt GUI for Gold/Silver ratio tracker."""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from silver_gold_tracker import RatioTracker, create_provider_chain, load_price_history, load_ratio_history

ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / "user_settings.json"


def _resolve_eastern_tz() -> ZoneInfo | None:
    try:
        return ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        return None


EASTERN_TZ = _resolve_eastern_tz()

PALETTES = {
    "Desert Ember": {
        "theme": "light",
        "bg": "#f5efe6",
        "surface": "#fff8f0",
        "text": "#2c1f14",
        "accent": "#c96f2d",
        "history": "#a05a2c",
        "live": "#d77a3f",
        "grid": "#d9c7b2",
        "island_bg": "#fff0e0",
    },
    "Slate Tide": {
        "theme": "dark",
        "bg": "#111827",
        "surface": "#1f2937",
        "text": "#e5e7eb",
        "accent": "#3b82f6",
        "history": "#60a5fa",
        "live": "#22d3ee",
        "grid": "#334155",
        "island_bg": "#0f172a",
    },
    "Midnight Mint": {
        "theme": "dark",
        "bg": "#0b1220",
        "surface": "#111827",
        "text": "#d1fae5",
        "accent": "#10b981",
        "history": "#34d399",
        "live": "#6ee7b7",
        "grid": "#22303f",
        "island_bg": "#07121a",
    },
    "Lavender Mist": {
        "theme": "light",
        "bg": "#f5f3ff",
        "surface": "#ffffff",
        "text": "#312e81",
        "accent": "#7c3aed",
        "history": "#8b5cf6",
        "live": "#a78bfa",
        "grid": "#ddd6fe",
        "island_bg": "#ede9fe",
    },
    "Carbon Neon": {
        "theme": "dark",
        "bg": "#0a0a0f",
        "surface": "#15151f",
        "text": "#f5f5ff",
        "accent": "#39ff14",
        "history": "#00e5ff",
        "live": "#ff2bd6",
        "grid": "#2a2f3c",
        "island_bg": "#10131d",
    },
    "Deep Ocean": {
        "theme": "dark",
        "bg": "#06141f",
        "surface": "#0b2536",
        "text": "#d4f1f9",
        "accent": "#38bdf8",
        "history": "#22d3ee",
        "live": "#2dd4bf",
        "grid": "#1f3c52",
        "island_bg": "#082032",
    },
    "Plum Night": {
        "theme": "dark",
        "bg": "#140f1d",
        "surface": "#23162f",
        "text": "#f5eaff",
        "accent": "#c084fc",
        "history": "#a78bfa",
        "live": "#f472b6",
        "grid": "#3b2a4d",
        "island_bg": "#1d122a",
    },
    "Monochrome High Contrast": {
        "theme": "dark",
        "bg": "#000000",
        "surface": "#111111",
        "text": "#ffffff",
        "accent": "#ffffff",
        "history": "#d1d5db",
        "live": "#ffffff",
        "grid": "#4b5563",
        "island_bg": "#0b0b0b",
    },
    "Aurora Ice": {
        "theme": "dark",
        "bg": "#0b1220",
        "surface": "#121c2f",
        "text": "#e6f1ff",
        "accent": "#7dd3fc",
        "history": "#38bdf8",
        "live": "#22d3ee",
        "grid": "#22314a",
        "island_bg": "#0d1728",
    },
    "Neon Orchard": {
        "theme": "dark",
        "bg": "#0e1410",
        "surface": "#152019",
        "text": "#eafceb",
        "accent": "#84cc16",
        "history": "#a3e635",
        "live": "#22c55e",
        "grid": "#2a3a2e",
        "island_bg": "#101b14",
    },
    "Rose Quartz Night": {
        "theme": "dark",
        "bg": "#1a1320",
        "surface": "#261a30",
        "text": "#fce7f3",
        "accent": "#f472b6",
        "history": "#fb7185",
        "live": "#e879f9",
        "grid": "#3a2945",
        "island_bg": "#201528",
    },
    "Copper Circuit": {
        "theme": "dark",
        "bg": "#1a120e",
        "surface": "#261a14",
        "text": "#fcefe5",
        "accent": "#f97316",
        "history": "#fb923c",
        "live": "#ea580c",
        "grid": "#4a3225",
        "island_bg": "#20150f",
    },
    "Polar Dawn": {
        "theme": "light",
        "bg": "#f5faff",
        "surface": "#ffffff",
        "text": "#0f172a",
        "accent": "#0284c7",
        "history": "#0ea5e9",
        "live": "#06b6d4",
        "grid": "#d6e8f5",
        "island_bg": "#ecf6fd",
    },
    "Cherry Blossom": {
        "theme": "light",
        "bg": "#fff7fa",
        "surface": "#ffffff",
        "text": "#4a1d2f",
        "accent": "#db2777",
        "history": "#f472b6",
        "live": "#fb7185",
        "grid": "#f3d5e4",
        "island_bg": "#fdecf4",
    },
    "Moss Paper": {
        "theme": "light",
        "bg": "#f6faf4",
        "surface": "#ffffff",
        "text": "#1f3a2d",
        "accent": "#2f855a",
        "history": "#38a169",
        "live": "#68d391",
        "grid": "#dcecdc",
        "island_bg": "#eef7ee",
    },
    "Crimson Slate": {
        "theme": "dark",
        "bg": "#16181d",
        "surface": "#22252b",
        "text": "#f3f4f6",
        "accent": "#ef4444",
        "history": "#f87171",
        "live": "#fb7185",
        "grid": "#363b44",
        "island_bg": "#1a1d23",
    },
    "Blue Steel": {
        "theme": "light",
        "bg": "#eef3f8",
        "surface": "#ffffff",
        "text": "#1e293b",
        "accent": "#2563eb",
        "history": "#3b82f6",
        "live": "#0ea5e9",
        "grid": "#d7e3ef",
        "island_bg": "#eaf2fa",
    },
    "Honeycomb": {
        "theme": "light",
        "bg": "#fff9ec",
        "surface": "#ffffff",
        "text": "#4a3a14",
        "accent": "#d97706",
        "history": "#f59e0b",
        "live": "#fbbf24",
        "grid": "#f1e3bd",
        "island_bg": "#fff4d6",
    },
    "Amber Terminal": {
        "theme": "dark",
        "bg": "#120d04",
        "surface": "#1f1608",
        "text": "#ffd27a",
        "accent": "#ffb020",
        "history": "#ffbf47",
        "live": "#ffdd99",
        "grid": "#5a3d10",
        "island_bg": "#1a1206",
    },
}

DEFAULT_SETTINGS = {
    "palette": "Slate Tide",
    "font_family": "Segoe UI",
    "font_size": 11,
    "font_weight": "Normal",
    "history_width": 2,
    "live_width": 2,
    "live_interval": "30s",
    "lock_x": False,
    "lock_y": False,
    "interaction_mode": "normal",
    "crosshair_auto_hover": False,
    "interaction_gain": 1.0,
    "skip_quality_checks": False,
    "provider_config": {
        "twelve": {"api_token": "", "api_base_url": ""},
        "metalsapi": {"api_token": "", "api_base_url": ""},
        "polygon": {"api_token": "", "api_base_url": ""},
    },
}


class StatusIsland(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusIsland")
        self.setStyleSheet("QFrame#statusIsland{border-radius:14px;padding:6px;}")
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(12)
        self.mode = QtWidgets.QLabel("IDLE")
        self.provider = QtWidgets.QLabel("stooq")
        self.activity = QtWidgets.QLabel("Ready")
        self.updated = QtWidgets.QLabel("-")
        for w in [self.mode, self.provider, self.activity, self.updated]:
            row.addWidget(w)

    def set_state(self, mode: str, provider: str, activity: str, updated: str) -> None:
        self.mode.setText(mode)
        self.provider.setText(provider)
        self.activity.setText(activity)
        self.updated.setText(updated)


class ThemeTile(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)

    def __init__(self, name: str, palette: dict[str, str]) -> None:
        super().__init__()
        self.name = name
        self.setObjectName("themeTile")
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        swatch = QtWidgets.QFrame()
        swatch.setMinimumHeight(88)
        swatch_layout = QtWidgets.QVBoxLayout(swatch)
        swatch_layout.setContentsMargins(8, 8, 8, 8)
        swatch_layout.setSpacing(6)
        swatch.setStyleSheet(
            f"QFrame {{ background: {palette['bg']}; border: 1px solid {palette['grid']}; border-radius: 8px; }}"
        )

        top_band = QtWidgets.QFrame()
        top_band.setMinimumHeight(28)
        top_band.setStyleSheet(
            f"QFrame {{ background: {palette['surface']}; border: 1px solid {palette['grid']}; border-radius: 6px; }}"
        )

        line_row = QtWidgets.QHBoxLayout()
        line_row.setContentsMargins(0, 0, 0, 0)
        line_row.setSpacing(6)
        history_line = QtWidgets.QFrame()
        history_line.setFixedHeight(6)
        history_line.setStyleSheet(f"QFrame {{ background: {palette['history']}; border-radius: 3px; }}")
        live_line = QtWidgets.QFrame()
        live_line.setFixedHeight(6)
        live_line.setStyleSheet(f"QFrame {{ background: {palette['live']}; border-radius: 3px; }}")
        accent_chip = QtWidgets.QFrame()
        accent_chip.setFixedSize(18, 18)
        accent_chip.setStyleSheet(
            f"QFrame {{ background: {palette['accent']}; border: 1px solid {palette['grid']}; border-radius: 9px; }}"
        )
        line_row.addWidget(history_line, 1)
        line_row.addWidget(live_line, 1)
        line_row.addWidget(accent_chip, 0)

        swatch_layout.addWidget(top_band)
        swatch_layout.addLayout(line_row)

        label = QtWidgets.QLabel(name)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setWordWrap(True)
        label.setStyleSheet("font-weight: 600;")

        layout.addWidget(swatch)
        layout.addWidget(label)
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet(
                "QFrame#themeTile { border: 2px solid #3b82f6; border-radius: 12px; }"
                "QFrame#themeTile:focus { border: 2px solid #2563eb; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#themeTile { border: 1px solid #6b7280; border-radius: 12px; }"
                "QFrame#themeTile:focus { border: 2px solid #3b82f6; }"
            )

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space):
            self.clicked.emit(self.name)
            event.accept()
            return
        super().keyPressEvent(event)


class MetricCard(QtWidgets.QFrame):
    clicked = QtCore.Signal()

    def __init__(self, title: str, selectable: bool) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self._selected = False
        self._bg_idle = QtGui.QColor("#1f2937")
        self._bg_selected = QtGui.QColor("#0f172a")
        self._border_idle = QtGui.QColor("#334155")
        self._border_selected = QtGui.QColor("#3b82f6")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        self.title = QtWidgets.QLabel(title)
        self.title.setObjectName("metricTitle")
        layout.addWidget(self.title, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor if selectable else QtCore.Qt.CursorShape.ArrowCursor)
        )
        self._selectable = selectable

    def add_value_widget(self, widget: QtWidgets.QWidget) -> None:
        value_shell = QtWidgets.QFrame()
        value_shell.setObjectName("metricValueShell")
        value_shell.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        shell_layout = QtWidgets.QVBoxLayout(value_shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.addWidget(widget)
        self.layout().addWidget(value_shell)  # type: ignore[union-attr]

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def set_theme_colors(
        self,
        *,
        bg_idle: str,
        bg_selected: str,
        border_idle: str,
        border_selected: str,
    ) -> None:
        self._bg_idle = QtGui.QColor(bg_idle)
        self._bg_selected = QtGui.QColor(bg_selected)
        self._border_idle = QtGui.QColor(border_idle)
        self._border_selected = QtGui.QColor(border_selected)
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._selectable and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = 10
        bg = self._bg_selected if self._selected else self._bg_idle
        border = self._border_selected if self._selected else self._border_idle
        painter.setBrush(bg)
        pen = QtGui.QPen(border, 2 if self._selected else 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, radius, radius)
        super().paintEvent(event)


class HoverMenuToolButton(QtWidgets.QToolButton):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._menu_obj: QtWidgets.QMenu | None = None
        self._hover_state = "idle"
        self._open_timer = QtCore.QTimer(self)
        self._open_timer.setSingleShot(True)
        self._open_timer.setInterval(140)
        self._open_timer.timeout.connect(self._open_menu)

        self._close_timer = QtCore.QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.setInterval(280)
        self._close_timer.timeout.connect(self._close_menu_if_outside)

    def setMenu(self, menu: QtWidgets.QMenu | None) -> None:  # type: ignore[override]
        if self._menu_obj is not None:
            self._menu_obj.removeEventFilter(self)
        self._menu_obj = menu
        super().setMenu(menu)
        if menu is not None:
            menu.installEventFilter(self)
            menu.aboutToHide.connect(self._on_menu_hidden)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        super().enterEvent(event)
        self._hover_state = "opening"
        self._close_timer.stop()
        if self.menu() is not None and not self.menu().isVisible() and not self._open_timer.isActive():
            self._open_timer.start()

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        super().leaveEvent(event)
        self._hover_state = "closing"
        self._open_timer.stop()
        if not self._close_timer.isActive():
            self._close_timer.start()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self.menu():
            if event.type() in (QtCore.QEvent.Type.Enter, QtCore.QEvent.Type.HoverEnter):
                self._hover_state = "open"
                self._close_timer.stop()
            elif event.type() in (QtCore.QEvent.Type.Leave, QtCore.QEvent.Type.HoverLeave):
                self._hover_state = "closing"
                if not self._close_timer.isActive():
                    self._close_timer.start()
        return super().eventFilter(watched, event)

    def showMenu(self) -> None:  # type: ignore[override]
        menu = self.menu()
        if menu is None:
            return
        anchor = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        if hasattr(menu, "_popup_halo_margins"):
            left, top, _, _ = menu._popup_halo_margins()  # type: ignore[attr-defined]
            anchor -= QtCore.QPoint(left, top)
        screen = QtGui.QGuiApplication.screenAt(anchor) or QtGui.QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            size_hint = menu.sizeHint()
            x = min(max(anchor.x(), available.left()), max(available.left(), available.right() - size_hint.width()))
            y = min(max(anchor.y(), available.top()), max(available.top(), available.bottom() - size_hint.height()))
            anchor = QtCore.QPoint(x, y)
        menu.popup(anchor)
        self.setDown(True)

    def _is_pointer_over_trigger_or_menu(self) -> bool:
        menu = self.menu()
        pointer = QtGui.QCursor.pos()
        button_rect = QtCore.QRect(self.mapToGlobal(QtCore.QPoint(0, 0)), self.size())
        if button_rect.contains(pointer):
            return True
        if menu is not None and menu.isVisible() and menu.geometry().contains(pointer):
            return True
        return False

    def _open_menu(self) -> None:
        menu = self.menu()
        if menu is None or menu.isVisible():
            return
        if self._hover_state in {"opening", "open"} and self._is_pointer_over_trigger_or_menu():
            self._hover_state = "open"
            self.showMenu()

    def _close_menu_if_outside(self) -> None:
        menu = self.menu()
        if menu is None or not menu.isVisible():
            return
        if self._is_pointer_over_trigger_or_menu():
            return
        self._hover_state = "idle"
        menu.close()

    def _on_menu_hidden(self) -> None:
        self._hover_state = "idle"
        self._open_timer.stop()
        self._close_timer.stop()
        self.clearFocus()
        self.update()


class ComboPopupItemDelegate(QtWidgets.QStyledItemDelegate):
    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> QtCore.QSize:
        base = super().sizeHint(option, index)
        min_height = option.fontMetrics.height() + 14
        return QtCore.QSize(base.width(), max(base.height(), min_height))


class TooltipEventBlocker(QtCore.QObject):
    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ToolTip:
            return True
        return super().eventFilter(watched, event)


@dataclass(frozen=True)
class HaloLayer:
    expansion: int
    alpha: int


@dataclass(frozen=True)
class PopupVisualProfile:
    top_margin: int
    side_margin: int
    bottom_margin: int
    layers: tuple[HaloLayer, ...]


class LiquidGlassPopupMixin:
    # Popup rendering source of truth (non-negotiable):
    # - No default/native OS or Qt popup shadow is allowed.
    # - Rounded popup body + subtle border only.
    # - Ambient halo is rendered outside body with blur-first falloff.
    # - Halo must preserve rounded silhouettes (no rectangular artifacts).
    # - attached_dropdown profile emphasizes side+bottom halo with minimal top halo.
    # - floating_menu profile uses symmetric halo on every side.
    # - Blur spread dominates over darkness; never a heavy directional drop shadow.
    POPUP_PROFILES = {
        "attached_dropdown": PopupVisualProfile(
            top_margin=6,
            side_margin=20,
            bottom_margin=24,
            layers=(HaloLayer(8, 30), HaloLayer(14, 20), HaloLayer(22, 12)),
        ),
        "floating_menu": PopupVisualProfile(
            top_margin=18,
            side_margin=20,
            bottom_margin=20,
            layers=(HaloLayer(8, 32), HaloLayer(14, 22), HaloLayer(22, 13)),
        ),
        "flat_dropdown": PopupVisualProfile(
            top_margin=0,
            side_margin=0,
            bottom_margin=0,
            layers=(),
        ),
    }

    def _init_liquid_popup(
        self,
        *,
        profile_name: str,
        corner_radius: int = 12,
    ) -> None:
        self._popup_profile_name = profile_name
        self._popup_corner_radius = corner_radius
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(QtCore.Qt.WindowType.NoDropShadowWindowHint, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _popup_profile(self) -> PopupVisualProfile:
        return self.POPUP_PROFILES.get(self._popup_profile_name, self.POPUP_PROFILES["floating_menu"])

    def _popup_halo_margins(self) -> tuple[int, int, int, int]:
        profile = self._popup_profile()
        return profile.side_margin, profile.top_margin, profile.side_margin, profile.bottom_margin

    def _popup_content_rect(self) -> QtCore.QRectF:
        left, top, right, bottom = self._popup_halo_margins()
        return QtCore.QRectF(self.rect().adjusted(left, top, -right, -bottom))

    def _paint_liquid_glass_surface(
        self,
        painter: QtGui.QPainter,
        *,
        body_color: QtGui.QColor,
        border_color: QtGui.QColor,
        halo_tint: QtGui.QColor,
    ) -> None:
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        profile = self._popup_profile()
        content_rect = self._popup_content_rect()
        radius = float(self._popup_corner_radius)
        for layer in reversed(profile.layers):
            spread_steps = 4
            for step in range(spread_steps):
                ratio = (step + 1) / spread_steps
                grow = int(layer.expansion * ratio)
                rect = content_rect.adjusted(-grow, -grow, grow, grow)
                alpha = max(1, int(layer.alpha * (1 - (step / spread_steps))))
                if self._popup_profile_name == "attached_dropdown" and rect.top() < content_rect.top():
                    top_distance = content_rect.top() - rect.top()
                    alpha = max(1, int(alpha * max(0.12, 1 - (top_distance / max(1.0, profile.top_margin + layer.expansion)))))
                ring_path = QtGui.QPainterPath()
                ring_path.addRoundedRect(rect, radius + grow, radius + grow)
                inner_path = QtGui.QPainterPath()
                inner_path.addRoundedRect(content_rect, radius, radius)
                ring_path = ring_path.subtracted(inner_path)

                gradient = QtGui.QRadialGradient(content_rect.center(), max(rect.width(), rect.height()) * 0.6)
                inner_color = QtGui.QColor(halo_tint)
                inner_color.setAlpha(alpha)
                outer_color = QtGui.QColor(halo_tint)
                outer_color.setAlpha(0)
                gradient.setColorAt(0.0, inner_color)
                gradient.setColorAt(1.0, outer_color)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.fillPath(ring_path, QtGui.QBrush(gradient))
        painter.setBrush(body_color)
        painter.setPen(QtGui.QPen(border_color, 1))
        painter.drawRoundedRect(content_rect, radius, radius)
        painter.restore()


class LiquidGlassMenu(LiquidGlassPopupMixin, QtWidgets.QMenu):
    def __init__(self, parent: QtWidgets.QWidget | None = None, *, profile_name: str = "floating_menu") -> None:
        super().__init__(parent)
        self._init_liquid_popup(profile_name=profile_name, corner_radius=12)
        self._body_color = QtGui.QColor("#1f2937")
        self._border_color = QtGui.QColor("#334155")
        self._halo_tint = QtGui.QColor("#3b82f6")
        left, top, right, bottom = self._popup_halo_margins()
        self.setContentsMargins(left, top, right, bottom)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_surface_colors(self, body_color: str, border_color: str, halo_tint: str) -> None:
        self._body_color = QtGui.QColor(body_color)
        self._border_color = QtGui.QColor(border_color)
        self._halo_tint = QtGui.QColor(halo_tint)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        self._paint_liquid_glass_surface(
            painter,
            body_color=self._body_color,
            border_color=self._border_color,
            halo_tint=self._halo_tint,
        )
        super().paintEvent(event)


class StableComboBox(QtWidgets.QComboBox):
    def __init__(self) -> None:
        super().__init__()
        self._text_left_padding = 10
        self._text_right_padding = 30

    def set_current_by_value(self, value: str, fallback: str | None = None) -> None:
        target = (value or "").strip()
        match_index = -1
        for idx in range(self.count()):
            item_text = self.itemText(idx)
            if item_text == target or item_text.casefold() == target.casefold():
                match_index = idx
                break
        if match_index >= 0:
            self.setCurrentIndex(match_index)
            return
        if fallback is not None:
            self.set_current_by_value(fallback)

    def _display_text(self) -> str:
        if self.currentIndex() >= 0:
            return self.itemText(self.currentIndex())
        return self.placeholderText().strip()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        display_text = self._display_text()
        visible_text = self.fontMetrics().elidedText(
            display_text,
            QtCore.Qt.TextElideMode.ElideRight,
            max(0, self.width() - (self._text_left_padding + self._text_right_padding)),
        )
        option.currentText = ""
        painter = QtWidgets.QStylePainter(self)
        option.rect = self.rect()
        painter.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_ComboBox, option)
        text_rect = self.style().subControlRect(
            QtWidgets.QStyle.ComplexControl.CC_ComboBox,
            option,
            QtWidgets.QStyle.SubControl.SC_ComboBoxEditField,
            self,
        ).adjusted(self._text_left_padding, 0, -self._text_right_padding, 0)
        text_color = self.palette().color(QtGui.QPalette.ColorRole.Text)
        if self.currentIndex() < 0 and self.placeholderText().strip():
            text_color = self.palette().color(QtGui.QPalette.ColorRole.PlaceholderText)
        painter.setPen(text_color)
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, visible_text)



class SensitiveViewBox(pg.ViewBox):
    # Baseline wheel zoom step per detent; lower values reduce jumpiness.
    WHEEL_BASE = 0.08
    # Multiplicative wheel tuning gain for quick global adjustments.
    WHEEL_GAIN = 1.0
    # Slow-wheel lower clamp to avoid overly weak zoom.
    MIN_EFFECTIVE_GAIN = 0.04
    # Fast-wheel upper clamp to keep zoom controllable.
    MAX_EFFECTIVE_GAIN = 0.22
    # Drag sensitivity multiplier; <1.0 gives finer pan control.
    PAN_GAIN = 0.82
    # Wheel cadence (seconds) that starts acceleration boost.
    SPEED_DT_FAST = 0.08
    # Wheel cadence (seconds) that returns to baseline behavior.
    SPEED_DT_SLOW = 0.45
    # Maximum multiplicative acceleration from rapid wheel events.
    SPEED_BOOST_MAX = 1.8

    def __init__(self, *args, interaction_gain: float = 1.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._interaction_gain = interaction_gain
        self._last_wheel_ts: float | None = None

    def _effective_wheel_gain(self) -> float:
        now = time.monotonic()
        if self._last_wheel_ts is None:
            self._last_wheel_ts = now
            speed_boost = 1.0
        else:
            dt_seconds = max(1e-3, now - self._last_wheel_ts)
            self._last_wheel_ts = now
            if dt_seconds <= self.SPEED_DT_FAST:
                speed_boost = self.SPEED_BOOST_MAX
            elif dt_seconds >= self.SPEED_DT_SLOW:
                speed_boost = 1.0
            else:
                blend = (self.SPEED_DT_SLOW - dt_seconds) / (self.SPEED_DT_SLOW - self.SPEED_DT_FAST)
                speed_boost = 1.0 + (self.SPEED_BOOST_MAX - 1.0) * blend

        gain = self.WHEEL_BASE * self.WHEEL_GAIN * self._interaction_gain * speed_boost
        return max(self.MIN_EFFECTIVE_GAIN, min(self.MAX_EFFECTIVE_GAIN, gain))

    def wheelEvent(self, ev, axis=None) -> None:  # noqa: ANN001
        delta = ev.delta() if hasattr(ev, "delta") else 0
        if delta == 0:
            ev.ignore()
            return

        steps = delta / 120.0
        wheel_gain = self._effective_wheel_gain()
        zoom_step = (1.0 + wheel_gain) ** (-steps)
        center = self.mapSceneToView(ev.scenePos())

        x_scale = zoom_step if axis in (None, 0) and self.state["mouseEnabled"][0] else None
        y_scale = zoom_step if axis in (None, 1) and self.state["mouseEnabled"][1] else None
        self.scaleBy(x=x_scale, y=y_scale, center=center)
        self.sigRangeChangedManually.emit(self.state["mouseEnabled"])
        ev.accept()

    def mouseDragEvent(self, ev, axis=None) -> None:  # noqa: ANN001
        if ev.button() != QtCore.Qt.MouseButton.LeftButton:
            super().mouseDragEvent(ev, axis=axis)
            return
        if self.state["mouseMode"] != self.PanMode:
            super().mouseDragEvent(ev, axis=axis)
            return
        if ev.isFinish():
            ev.accept()
            return

        delta = ev.pos() - ev.lastPos()
        px, py = self.viewPixelSize()
        pan_scale = self.PAN_GAIN * self._interaction_gain
        x_shift = -delta.x() * px * pan_scale if self.state["mouseEnabled"][0] else None
        y_shift = delta.y() * py * pan_scale if self.state["mouseEnabled"][1] else None
        self.translateBy(x=x_shift, y=y_shift)
        self.sigRangeChangedManually.emit(self.state["mouseEnabled"])
        ev.accept()


class TrackerWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = self._load_settings()
        self._busy = False
        self._source_dirty = False
        self._grid_visible = True
        self._floating_surfaces: list[QtWidgets.QWidget] = []
        self._tooltip_blocker = TooltipEventBlocker(self)
        QtWidgets.QApplication.instance().installEventFilter(self._tooltip_blocker)

        self.setWindowTitle("Gold/Silver Ratio Tracker")
        self.resize(1280, 820)

        self.historical_points: list[tuple[dt.datetime, float]] = []
        self.live_points: list[tuple[dt.datetime, float]] = []
        self.active_chart = "ratio"
        self.history_store: dict[str, list[tuple[dt.datetime, float]]] = {}
        self.history_context: tuple[str, str] | None = None
        self.chart_view_ranges: dict[str, tuple[list[float], list[float]]] = {}
        self._interaction_mode = "normal"
        self._auto_hover_active = False
        self._mode_indicator_anim: QtCore.QPropertyAnimation | None = None

        self.provider_combo = StableComboBox()
        self.provider_combo.addItems(["stooq", "yahoo", "google", "twelve", "metalsapi", "polygon"])
        self.fallback_combo = StableComboBox()
        self.fallback_combo.addItems(["none", "stooq", "yahoo", "google", "twelve", "metalsapi", "polygon"])
        self._refresh_provider_availability()

        self.history_combo = StableComboBox()
        self.history_combo.addItems(["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "MAX"])
        self.history_combo.setPlaceholderText("Select history")
        self.history_combo.set_current_by_value("1Y")

        self.interval_combo = StableComboBox()
        self.interval_combo.addItems(["10s", "30s", "1m", "5m"])
        self.interval_combo.setPlaceholderText("Select interval")
        self.interval_combo.set_current_by_value(str(self.settings.get("live_interval", "30s")), fallback="30s")
        self.interval_combo.currentTextChanged.connect(self._on_interval_change)
        self._init_combo_popup_views()

        self.lock_x_btn = QtWidgets.QToolButton()
        self.lock_x_btn.setText("X Lock")
        self.lock_x_btn.setCheckable(True)
        self.lock_x_btn.setChecked(bool(self.settings.get("lock_x", False)))
        self.lock_y_btn = QtWidgets.QToolButton()
        self.lock_y_btn.setText("Y Lock")
        self.lock_y_btn.setCheckable(True)
        self.lock_y_btn.setChecked(bool(self.settings.get("lock_y", False)))
        self.mode_segment = QtWidgets.QFrame()
        self.mode_segment.setObjectName("modeSegment")
        self.mode_normal_btn = QtWidgets.QToolButton()
        self.mode_normal_btn.setText("Normal")
        self.mode_normal_btn.setCheckable(True)
        self.mode_crosshair_btn = QtWidgets.QToolButton()
        self.mode_crosshair_btn.setText("Crosshair")
        self.mode_crosshair_btn.setCheckable(True)
        self.mode_indicator = QtWidgets.QFrame(self.mode_segment)
        self.mode_indicator.setObjectName("modeSegmentIndicator")
        self.mode_indicator.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.mode_indicator.hide()
        self.mode_group = QtWidgets.QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.mode_normal_btn)
        self.mode_group.addButton(self.mode_crosshair_btn)

        self.gold_label = QtWidgets.QLabel("-")
        self.silver_label = QtWidgets.QLabel("-")
        self.ratio_label = QtWidgets.QLabel("-")
        self.updated_label = QtWidgets.QLabel("-")
        self.status_label = QtWidgets.QLabel("Load history, then use Snapshot or Start Live")

        self.status_island = StatusIsland()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.snapshot)
        self._on_interval_change(self.interval_combo.currentText())

        self.tracker = self._make_tracker()

        interaction_gain = self._sanitize_interaction_gain(self.settings.get("interaction_gain", 1.0))
        self.settings["interaction_gain"] = interaction_gain
        self.plot_widget = pg.PlotWidget(
            viewBox=SensitiveViewBox(interaction_gain=interaction_gain),
            axisItems={"bottom": pg.DateAxisItem()},
        )
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel("left", "G/S")
        self.plot_widget.setLabel("bottom", "Time")
        self.legend = self.plot_widget.addLegend()
        self._applying_bounds = False
        self.plot_widget.getViewBox().setMenuEnabled(False)
        self.plot_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.plot_widget.customContextMenuRequested.connect(self._show_plot_menu)

        self.hist_curve = self.plot_widget.plot([], [], name="History")
        self.live_curve = self.plot_widget.plot([], [], name="Live")
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._on_range_changed)
        self.crosshair_vline = pg.InfiniteLine(angle=90, movable=False)
        self.crosshair_hline = pg.InfiniteLine(angle=0, movable=False)
        self.crosshair_label = pg.TextItem(anchor=(0, 1))
        self.plot_widget.addItem(self.crosshair_vline, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_hline, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_label, ignoreBounds=True)
        self._set_crosshair_visible(False)
        self.mouse_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_scene_mouse_moved,
        )
        self.plot_widget.scene().sigMouseHover.connect(self._on_scene_mouse_hover)

        self.lock_x_btn.toggled.connect(lambda _checked: self._save_settings())
        self.lock_y_btn.toggled.connect(lambda _checked: self._save_settings())
        self.mode_normal_btn.toggled.connect(lambda checked: checked and self._set_interaction_mode("normal"))
        self.mode_crosshair_btn.toggled.connect(lambda checked: checked and self._set_interaction_mode("crosshair"))
        self.provider_combo.currentTextChanged.connect(self._on_source_selection_changed)
        self.fallback_combo.currentTextChanged.connect(self._on_source_selection_changed)

        self._build_ui()
        self._apply_visual_settings()
        self._set_interaction_mode(str(self.settings.get("interaction_mode", "normal")), animate=False)
        QtCore.QTimer.singleShot(0, lambda: self._update_mode_indicator(animated=False))
        self._set_active_chart("ratio")
        self._sync_controls_state()
        self._update_status_island("IDLE", "Ready")

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        v = QtWidgets.QVBoxLayout(root)

        top = QtWidgets.QHBoxLayout()
        top.addStretch(1)
        top.addWidget(self.status_island)
        top.addStretch(1)

        source_controls = QtWidgets.QHBoxLayout()
        source_controls.addWidget(QtWidgets.QLabel("Provider"))
        source_controls.addWidget(self.provider_combo)
        source_controls.addWidget(QtWidgets.QLabel("Fallback"))
        source_controls.addWidget(self.fallback_combo)
        source_controls.addWidget(QtWidgets.QLabel("History"))
        source_controls.addWidget(self.history_combo)
        source_controls.addWidget(QtWidgets.QLabel("Live every"))
        source_controls.addWidget(self.interval_combo)
        source_controls.addStretch(1)

        def btn(name: str, fn) -> QtWidgets.QPushButton:
            b = QtWidgets.QPushButton(name)
            b.clicked.connect(fn)
            return b

        action_controls = QtWidgets.QHBoxLayout()
        self.btn_apply_source = btn("Apply Source", self.apply_source)
        self.btn_load_history = btn("Load History", self.load_history)
        self.btn_snapshot = btn("Snapshot", self.snapshot)
        self.btn_start_live = btn("Start Live", self.start_live)
        self.btn_pause_live = btn("Pause Live", self.pause_live)
        action_controls.addWidget(self.btn_apply_source)
        action_controls.addWidget(self.btn_load_history)
        action_controls.addWidget(self.btn_snapshot)
        action_controls.addWidget(self.btn_start_live)
        action_controls.addWidget(self.btn_pause_live)
        mode_segment_layout = QtWidgets.QHBoxLayout(self.mode_segment)
        mode_segment_layout.setContentsMargins(2, 2, 2, 2)
        mode_segment_layout.setSpacing(0)
        mode_segment_layout.addWidget(self.mode_normal_btn)
        mode_segment_layout.addWidget(self.mode_crosshair_btn)
        self.mode_indicator.lower()
        self.mode_normal_btn.raise_()
        self.mode_crosshair_btn.raise_()
        self.mode_segment.installEventFilter(self)
        self.mode_normal_btn.installEventFilter(self)
        self.mode_crosshair_btn.installEventFilter(self)
        action_controls.addWidget(self.mode_segment)
        action_controls.addWidget(self.lock_x_btn)
        action_controls.addWidget(self.lock_y_btn)
        self.btn_settings = btn("Settings", self.open_customization)

        more_btn = HoverMenuToolButton()
        more_btn.setText("More")
        more_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = LiquidGlassMenu(more_btn, profile_name="flat_dropdown")
        terminate_action = more_menu.addAction("Terminate Session")
        terminate_action.triggered.connect(self.terminate_session)
        more_btn.setMenu(more_menu)
        self._floating_surfaces.append(more_menu)

        action_controls.addWidget(more_btn)
        action_controls.addWidget(self.btn_settings)
        action_controls.addStretch(1)

        metrics = QtWidgets.QHBoxLayout()
        self.chart_cards: dict[str, MetricCard] = {}
        self.metric_cards: dict[str, MetricCard] = {}
        for name, widget, chart_key in [
            ("Gold", self.gold_label, "gold"),
            ("Silver", self.silver_label, "silver"),
            ("G/S", self.ratio_label, "ratio"),
            ("Updated", self.updated_label, None),
        ]:
            card = MetricCard(name, selectable=chart_key is not None)
            self.metric_cards[name.lower()] = card
            if chart_key is not None:
                card.clicked.connect(lambda key=chart_key: self._set_active_chart(key))
                self.chart_cards[chart_key] = card
            widget.setObjectName("metricValue")
            widget.setMinimumHeight(28)
            widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            card.add_value_widget(widget)
            metrics.addWidget(card)

        v.addLayout(top)
        v.addLayout(source_controls)
        v.addLayout(action_controls)
        v.addLayout(metrics)
        v.addWidget(self.plot_widget, 1)
        v.addWidget(self.status_label)

    def _load_settings(self) -> dict:
        if not SETTINGS_FILE.exists():
            return dict(DEFAULT_SETTINGS)
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            out = json.loads(json.dumps(DEFAULT_SETTINGS))
            self._deep_merge_dict(out, data)
            if out.get("palette") == "Sandstone":
                out["palette"] = "Desert Ember"
            return out
        except Exception:  # noqa: BLE001
            return dict(DEFAULT_SETTINGS)

    def _deep_merge_dict(self, out: dict, incoming: dict) -> None:
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                self._deep_merge_dict(out[key], value)
            else:
                out[key] = value

    def _sanitize_interaction_gain(self, value) -> float:  # noqa: ANN001
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 1.0
        return max(0.5, min(1.5, numeric))

    def _save_settings(self) -> None:
        self.settings["live_interval"] = self.interval_combo.currentText()
        self.settings["lock_x"] = self.lock_x_btn.isChecked()
        self.settings["lock_y"] = self.lock_y_btn.isChecked()
        self.settings["interaction_mode"] = self._interaction_mode
        SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2))

    def _init_combo_popup_views(self) -> None:
        for combo in [self.provider_combo, self.fallback_combo, self.history_combo, self.interval_combo]:
            view = QtWidgets.QListView(combo)
            view.setObjectName("comboPopup")
            view.setUniformItemSizes(False)
            view.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
            view.setSpacing(1)
            view.setItemDelegate(ComboPopupItemDelegate(view))
            combo.setView(view)
            popup_window = view.window()
            if popup_window is not None:
                popup_window.setWindowFlag(QtCore.Qt.WindowType.NoDropShadowWindowHint, True)
                popup_window.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint, True)
                popup_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self._floating_surfaces.append(view)
            if popup_window is not None:
                self._floating_surfaces.append(popup_window)

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)

    def _rgb_to_hex(self, rgb: tuple[int, int, int]) -> str:
        r, g, b = rgb
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"

    def _blend(self, c1: str, c2: str, ratio: float) -> str:
        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        mix = (
            int(r1 * (1 - ratio) + r2 * ratio),
            int(g1 * (1 - ratio) + g2 * ratio),
            int(b1 * (1 - ratio) + b2 * ratio),
        )
        return self._rgb_to_hex(mix)

    def _with_alpha(self, color: str, alpha: int) -> str:
        red, green, blue = self._hex_to_rgb(color)
        clamped = max(0, min(255, alpha))
        return f"rgba({red}, {green}, {blue}, {clamped})"

    def _relative_luminance(self, color: str) -> float:
        def channel_luma(channel: int) -> float:
            normalized = channel / 255
            if normalized <= 0.03928:
                return normalized / 12.92
            return ((normalized + 0.055) / 1.055) ** 2.4

        red, green, blue = self._hex_to_rgb(color)
        return (0.2126 * channel_luma(red)) + (0.7152 * channel_luma(green)) + (0.0722 * channel_luma(blue))

    def _contrast_ratio(self, left: str, right: str) -> float:
        l1 = self._relative_luminance(left)
        l2 = self._relative_luminance(right)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def _pick_contrast_color(self, background: str) -> str:
        white = "#ffffff"
        black = "#111111"
        return white if self._contrast_ratio(white, background) >= self._contrast_ratio(black, background) else black

    def _resolve_palette(self, palette: dict[str, str]) -> dict[str, str]:
        resolved = dict(palette)
        theme_kind = resolved.get("theme", "dark")
        if "disabled_bg" not in resolved:
            resolved["disabled_bg"] = self._blend(resolved["surface"], resolved["bg"], 0.45 if theme_kind == "dark" else 0.15)
        if "disabled_border" not in resolved:
            resolved["disabled_border"] = self._blend(resolved["grid"], resolved["bg"], 0.35)
        if "disabled_text" not in resolved:
            resolved["disabled_text"] = self._blend(resolved["text"], resolved["bg"], 0.55 if theme_kind == "dark" else 0.45)
        focus_ring = resolved.get("focus_ring", resolved["accent"])
        if self._contrast_ratio(focus_ring, resolved["surface"]) < 2.25:
            focus_ring = self._pick_contrast_color(resolved["surface"])
        resolved["focus_ring"] = focus_ring

        checked_hover_ring = resolved.get("checked_hover_ring", self._pick_contrast_color(resolved["accent"]))
        if self._contrast_ratio(checked_hover_ring, resolved["accent"]) < 2.25:
            checked_hover_ring = self._pick_contrast_color(checked_hover_ring)
        resolved["checked_hover_ring"] = checked_hover_ring
        resolved["accent_on"] = self._pick_contrast_color(resolved["accent"])
        return resolved

    def _build_crosshair_cursor(self, color: str) -> QtGui.QCursor:
        size = 27
        center = size // 2
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        outline = QtGui.QPen(QtGui.QColor(0, 0, 0, 140) if self._pick_contrast_color(color) == "#ffffff" else QtGui.QColor(255, 255, 255, 140), 3)
        main_pen = QtGui.QPen(QtGui.QColor(color), 1)
        painter.setPen(outline)
        painter.drawLine(center, 1, center, size - 2)
        painter.drawLine(1, center, size - 2, center)
        painter.setPen(main_pen)
        painter.drawLine(center, 1, center, size - 2)
        painter.drawLine(1, center, size - 2, center)
        painter.end()
        return QtGui.QCursor(pixmap, center, center)

    def _refresh_provider_availability(self) -> None:
        provider_config = self.settings.get("provider_config", {})
        premium_keys = {"twelve", "metalsapi", "polygon"}

        def has_key(provider_key: str) -> bool:
            cfg = provider_config.get(provider_key, {})
            return bool(str(cfg.get("api_token", "")).strip())

        for combo in [self.provider_combo, self.fallback_combo]:
            model = combo.model()
            for idx in range(combo.count()):
                raw = combo.itemText(idx)
                base = raw.split(" (API key required)")[0]
                item = model.item(idx) if hasattr(model, "item") else None
                blocked = base in premium_keys and not has_key(base)
                if blocked:
                    combo.setItemText(idx, f"{base} (API key required)")
                else:
                    combo.setItemText(idx, base)
                if item is not None:
                    item.setEnabled(not blocked)
            current_base = combo.currentText().split(" (API key required)")[0]
            if current_base in premium_keys and not has_key(current_base):
                combo.setCurrentText("none" if combo is self.fallback_combo else "stooq")

    def _sync_controls_state(self) -> None:
        live_on = self.timer.isActive()
        self.btn_start_live.setEnabled(not live_on and not self._busy)
        self.btn_pause_live.setEnabled(live_on and not self._busy)
        self.btn_apply_source.setEnabled(not self._busy)
        self.btn_load_history.setEnabled(not self._busy)
        self.btn_snapshot.setEnabled(not self._busy)
        self.btn_settings.setEnabled(not self._busy)
        self.btn_apply_source.setText("Apply Source *" if self._source_dirty else "Apply Source")

    def _apply_visual_settings(self) -> None:
        palette_name = self.settings.get("palette", "Slate Tide")
        palette = self._resolve_palette(PALETTES.get(palette_name, PALETTES["Slate Tide"]))
        self._active_palette = palette

        font = QtGui.QFont(self.settings.get("font_family", "Segoe UI"))
        font.setPointSize(int(self.settings.get("font_size", 11)))
        weight_map = {
            "Light": QtGui.QFont.Weight.Light,
            "Normal": QtGui.QFont.Weight.Normal,
            "Medium": QtGui.QFont.Weight.Medium,
            "Bold": QtGui.QFont.Weight.Bold,
        }
        font.setWeight(weight_map.get(self.settings.get("font_weight", "Normal"), QtGui.QFont.Weight.Normal))
        QtWidgets.QApplication.instance().setFont(font)
        base_font_pt = int(self.settings.get("font_size", 11))

        style = f"""
        QWidget {{ background: {palette['bg']}; color: {palette['text']}; }}
        QGroupBox {{
            background: {palette['surface']};
            border: 1px solid {palette['grid']};
            border-radius: 10px;
            margin-top: 14px;
            padding-top: 6px;
        }}
        QLabel#metricTitle {{
            font-weight: 600;
            color: {palette['text']};
            background: transparent;
        }}
        QFrame#metricValueShell {{
            background: transparent;
            border: none;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px 0 6px;
            background: {palette['surface']};
        }}
        QLabel#metricValue {{
            background: transparent;
            border: none;
            padding: 2px 2px;
            color: {palette['text']};
            font-size: 16px;
            font-weight: 600;
        }}
        QPushButton, QToolButton {{
            background: {palette['surface']};
            color: {palette['text']};
            border: 1px solid {palette['grid']};
            border-radius: 10px;
            padding: 6px 10px;
            min-height: 30px;
        }}
        QPushButton:hover, QToolButton:hover {{ border-color: {palette['accent']}; }}
        QPushButton:pressed, QToolButton:pressed {{ background: {palette['island_bg']}; }}
        QPushButton:disabled, QToolButton:disabled {{
            background: {palette['disabled_bg']};
            color: {palette['disabled_text']};
            border: 1px solid {palette['disabled_border']};
        }}
        QPushButton:focus, QToolButton:focus {{
            outline: none;
            border: 2px solid {palette['focus_ring']};
        }}
        QToolButton:checked {{
            background: {palette['accent']};
            color: {palette['accent_on']};
            border: 2px solid {palette['accent']};
            font-weight: 700;
        }}
        QToolButton:checked:hover {{
            border: 2px solid {palette['checked_hover_ring']};
        }}
        QFrame#modeSegment {{
            background: {palette['surface']};
            border: 1px solid {palette['grid']};
            border-radius: 11px;
        }}
        QFrame#modeSegment QFrame#modeSegmentIndicator {{
            background: {palette['accent']};
            border: none;
            border-radius: 8px;
        }}
        QFrame#modeSegment QToolButton {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 8px;
            margin: 0;
            min-width: 84px;
            padding: 6px 10px;
        }}
        QFrame#modeSegment QToolButton:hover {{
            background: {self._with_alpha(palette['accent'], 30)};
            border: 1px solid {self._with_alpha(palette['accent'], 80)};
        }}
        QFrame#modeSegment QToolButton:focus {{
            border: 1px solid {palette['focus_ring']};
            background: {self._with_alpha(palette['accent'], 36)};
        }}
        QFrame#modeSegment QToolButton:checked {{
            background: transparent;
            color: {palette['accent_on']};
            border: 1px solid transparent;
            font-weight: 700;
        }}
        QFrame#modeSegment QToolButton:checked:hover {{
            border: 1px solid transparent;
        }}
        QFrame#statusIsland {{ background: {palette['island_bg']}; border: 1px solid {palette['grid']}; }}
        QFrame#statusIsland QLabel {{
            background: transparent;
            border: none;
            color: {palette['text']};
        }}
        QTabWidget::pane {{
            border: 1px solid {palette['grid']};
            background: {palette['surface']};
        }}
        QTabBar::tab {{
            background: {palette['bg']};
            color: {palette['text']};
            border: 1px solid {palette['grid']};
            border-bottom: none;
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background: {palette['surface']};
            color: {palette['text']};
            border-color: {palette['accent']};
            font-weight: 600;
        }}
        QTabBar::tab:hover {{
            border-color: {palette['accent']};
        }}
        QMenu {{
            background: transparent;
            color: {palette['text']};
            border: none;
            border-radius: 12px;
            padding: 16px 18px 18px 18px;
            font-size: {base_font_pt}pt;
        }}
        QMenu::item {{
            padding: 8px 12px;
            border-radius: 8px;
            margin: 0;
        }}
        QMenu::item:selected {{
            background: {palette['island_bg']};
            border: 1px solid {palette['accent']};
            color: {palette['text']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {palette['grid']};
            margin: 6px 8px;
        }}
        QComboBox {{
            background: {palette['surface']};
            color: {palette['text']};
            border: 1px solid {palette['grid']};
            border-radius: 12px;
            padding: 5px 10px;
            min-height: 32px;
            font-size: {base_font_pt}pt;
        }}
        QComboBox:hover {{
            border-color: {palette['accent']};
        }}
        QComboBox:focus, QComboBox:on {{
            outline: none;
            border: 1px solid {palette['accent']};
            background: {palette['island_bg']};
        }}
        QComboBox::drop-down {{
            border: none;
            border-left: 1px solid {palette['grid']};
            width: 22px;
            margin-right: 4px;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
            background: {palette['bg']};
        }}
        QComboBox:disabled {{
            background: {palette['disabled_bg']};
            color: {palette['disabled_text']};
            border: 1px solid {palette['disabled_border']};
        }}
        QAbstractItemView#comboPopup {{
            background: {palette['surface']};
            color: {palette['text']};
            border: 1px solid {palette['grid']};
            border-radius: 12px;
            padding: 6px;
            font-size: {base_font_pt}pt;
            outline: none;
            selection-background-color: {palette['island_bg']};
            selection-color: {palette['text']};
        }}
        QAbstractItemView#comboPopup::viewport {{
            background: {palette['surface']};
            border: none;
        }}
        QAbstractItemView#comboPopup::item {{
            border-radius: 10px;
            margin: 0;
            padding: 8px 12px;
            min-height: 34px;
        }}
        QAbstractItemView#comboPopup::item:hover,
        QAbstractItemView#comboPopup::item:selected {{
            background: {palette['island_bg']};
            border: 1px solid {palette['accent']};
            color: {palette['text']};
        }}
        QAbstractItemView#comboPopup::item:disabled {{
            color: {palette['disabled_text']};
        }}
        QToolButton::menu-indicator {{
            subcontrol-origin: padding;
            subcontrol-position: right center;
            width: 10px;
        }}
        """
        self.setStyleSheet(style)
        for surface in self._floating_surfaces:
            if isinstance(surface, LiquidGlassMenu):
                surface.set_surface_colors(palette["surface"], palette["grid"], palette["accent"])
            elif surface is not None:
                surface.setGraphicsEffect(None)

        self.plot_widget.setBackground(palette["surface"])
        self.hist_curve.setPen(pg.mkPen(palette["history"], width=int(self.settings.get("history_width", 2))))
        self.live_curve.setPen(pg.mkPen(palette["live"], width=int(self.settings.get("live_width", 2))))
        crosshair_pen = pg.mkPen(palette["accent"], width=1.2)
        self.crosshair_vline.setPen(crosshair_pen)
        self.crosshair_hline.setPen(crosshair_pen)
        self.crosshair_label.setColor(palette["text"])
        self._crosshair_label_bg = self._with_alpha(palette["surface"], 236)
        self._crosshair_label_border = self._with_alpha(palette["grid"], 220)
        self._crosshair_label_subtle = self._blend(palette["text"], palette["surface"], 0.42)
        app_font = QtWidgets.QApplication.instance().font()
        self._crosshair_font_family = app_font.family().replace("'", "\\'")
        self._crosshair_font_size_pt = max(8, app_font.pointSize())
        self._crosshair_font_weight = max(400, min(700, int(app_font.weight())))
        crosshair_cursor_color = "#f8fafc" if palette.get("theme", "dark") == "dark" else "#101418"
        self._crosshair_cursor = self._build_crosshair_cursor(crosshair_cursor_color)
        self.mode_indicator.setStyleSheet(f"background: {palette['accent']}; border: none; border-radius: 8px;")
        self._apply_mode_cursor()
        self._update_mode_indicator(animated=False)
        for card in self.metric_cards.values():
            card.set_theme_colors(
                bg_idle=palette["surface"],
                bg_selected=palette["island_bg"],
                border_idle=palette["grid"],
                border_selected=palette["accent"],
            )
        self._grid_visible = True
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        if self.legend is not None:
            self.legend.setVisible(True)
        self._refresh_provider_availability()

    def _set_crosshair_visible(self, visible: bool) -> None:
        self.crosshair_vline.setVisible(visible)
        self.crosshair_hline.setVisible(visible)
        self.crosshair_label.setVisible(visible)

    def _apply_mode_cursor(self) -> None:
        view = self.plot_widget.viewport()
        if self._interaction_mode == "crosshair":
            view.setCursor(getattr(self, "_crosshair_cursor", QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor)))
        else:
            view.unsetCursor()
            view.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def _update_mode_indicator(self, *, animated: bool) -> None:
        active = self.mode_crosshair_btn if self._interaction_mode == "crosshair" else self.mode_normal_btn
        if active is None:
            return
        target = active.geometry().adjusted(2, 2, -2, -2)
        if target.width() <= 0 or target.height() <= 0:
            return
        self.mode_indicator.show()
        if not animated:
            self.mode_indicator.setGeometry(target)
            return
        if self._mode_indicator_anim is not None:
            self._mode_indicator_anim.stop()
        self._mode_indicator_anim = QtCore.QPropertyAnimation(self.mode_indicator, b"geometry", self)
        self._mode_indicator_anim.setDuration(150)
        self._mode_indicator_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._mode_indicator_anim.setStartValue(self.mode_indicator.geometry())
        self._mode_indicator_anim.setEndValue(target)
        self._mode_indicator_anim.start()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched in {self.mode_segment, self.mode_normal_btn, self.mode_crosshair_btn} and event.type() in {
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Move,
            QtCore.QEvent.Type.Show,
        }:
            self._update_mode_indicator(animated=False)
        return super().eventFilter(watched, event)

    def _format_crosshair_value(self, value: float) -> str:
        precision_map = {"gold": 2, "silver": 2, "ratio": 6}
        precision = precision_map.get(self.active_chart, 4)
        return f"{value:,.{precision}f}"

    def _update_crosshair_label(self, nearest_x: float, nearest_y: float, nearest_ts: dt.datetime) -> None:
        view_box = self.plot_widget.getViewBox()
        (x_min, x_max), (y_min, y_max) = view_box.viewRange()
        x_span = max(1e-9, x_max - x_min)
        y_span = max(1e-9, y_max - y_min)
        pad_x = x_span * 0.016
        pad_y = y_span * 0.028

        anchor_x = 0.0
        x_pos = nearest_x + pad_x
        if nearest_x > (x_min + (x_span * 0.76)):
            anchor_x = 1.0
            x_pos = nearest_x - pad_x

        anchor_y = 1.0
        y_pos = nearest_y + pad_y
        if nearest_y > (y_min + (y_span * 0.78)):
            anchor_y = 0.0
            y_pos = nearest_y - pad_y

        chart_label = {"gold": "Gold", "silver": "Silver", "ratio": "G/S"}.get(self.active_chart, "G/S")
        value_text = self._format_crosshair_value(nearest_y)
        timestamp_text = self._format_timestamp(nearest_ts)
        heading_size = max(8, self._crosshair_font_size_pt - 2)
        value_size = max(9, self._crosshair_font_size_pt + 1)
        timestamp_size = max(8, self._crosshair_font_size_pt - 2)
        self.crosshair_label.setAnchor((anchor_x, anchor_y))
        self.crosshair_label.setHtml(
            (
                "<div style='"
                f"background:{self._crosshair_label_bg};"
                f"border:1px solid {self._crosshair_label_border};"
                "border-radius:7px;"
                "padding:6px 8px;"
                "line-height:1.25;"
                f"font-family:\"{self._crosshair_font_family}\";"
                f"font-size:{self._crosshair_font_size_pt}pt;"
                f"font-weight:{self._crosshair_font_weight};"
                "'>"
                f"<div style='font-size:{heading_size}pt;color:{self._crosshair_label_subtle};font-weight:600'>{chart_label}</div>"
                f"<div style='font-size:{value_size}pt;color:{self._active_palette['text']};font-weight:700'>{value_text}</div>"
                f"<div style='font-size:{timestamp_size}pt;color:{self._crosshair_label_subtle}'>{timestamp_text}</div>"
                "</div>"
            )
        )
        self.crosshair_label.setPos(x_pos, y_pos)

    def _set_interaction_mode(self, mode: str, *, animate: bool = True) -> None:
        normalized = mode if mode in {"normal", "crosshair"} else "normal"
        self._interaction_mode = normalized
        self.settings["interaction_mode"] = normalized
        self.mode_normal_btn.blockSignals(True)
        self.mode_crosshair_btn.blockSignals(True)
        self.mode_normal_btn.setChecked(normalized == "normal")
        self.mode_crosshair_btn.setChecked(normalized == "crosshair")
        self.mode_normal_btn.blockSignals(False)
        self.mode_crosshair_btn.blockSignals(False)
        self._set_crosshair_visible(normalized == "crosshair")
        self._apply_mode_cursor()
        should_animate = animate and self.isVisible() and self.mode_indicator.geometry().isValid()
        self._update_mode_indicator(animated=should_animate)
        self._save_settings()

    def _all_chart_points(self) -> list[tuple[dt.datetime, float]]:
        points = self.historical_points + self.live_points
        return sorted(points, key=lambda p: p[0])

    def _crosshair_auto_hover_enabled(self) -> bool:
        return bool(self.settings.get("crosshair_auto_hover", False))

    def _on_scene_mouse_hover(self, items) -> None:  # noqa: ANN001
        if self._interaction_mode == "crosshair" or not self._crosshair_auto_hover_enabled():
            return
        hovering_plot = bool(items)
        if hovering_plot and not self._auto_hover_active:
            self._auto_hover_active = True
            self._set_crosshair_visible(True)
        elif not hovering_plot and self._auto_hover_active:
            self._auto_hover_active = False
            self._set_crosshair_visible(False)

    def _on_scene_mouse_moved(self, event) -> None:  # noqa: ANN001
        if self._interaction_mode != "crosshair" and not self._auto_hover_active:
            return
        if not event:
            self._set_crosshair_visible(False)
            return
        scene_pos = event[0]
        view_box = self.plot_widget.getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(scene_pos):
            self._set_crosshair_visible(False)
            if self._auto_hover_active and self._crosshair_auto_hover_enabled():
                self._auto_hover_active = False
            return
        points = self._all_chart_points()
        if not points:
            self._set_crosshair_visible(False)
            return

        view_point = view_box.mapSceneToView(scene_pos)
        target_x = view_point.x()
        nearest = min(points, key=lambda p: abs(p[0].timestamp() - target_x))
        nearest_x = nearest[0].timestamp()
        nearest_y = nearest[1]
        self.crosshair_vline.setPos(nearest_x)
        self.crosshair_hline.setPos(nearest_y)
        self._update_crosshair_label(nearest_x, nearest_y, nearest[0])
        self._set_crosshair_visible(True)

    def open_customization(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.resize(880, 640)
        dlg.setMinimumSize(760, 560)
        layout = QtWidgets.QVBoxLayout(dlg)

        tabs = QtWidgets.QTabWidget()

        appearance_tab = QtWidgets.QWidget()
        appearance_layout = QtWidgets.QVBoxLayout(appearance_tab)
        appearance_layout.addWidget(QtWidgets.QLabel("Themes"))
        palette_scroll = QtWidgets.QScrollArea()
        palette_scroll.setWidgetResizable(True)
        palette_container = QtWidgets.QWidget()
        palette_grid = QtWidgets.QGridLayout(palette_container)
        palette_grid.setContentsMargins(6, 6, 6, 6)
        palette_grid.setHorizontalSpacing(10)
        palette_grid.setVerticalSpacing(10)

        selected_palette_name = self.settings.get("palette", "Slate Tide")
        theme_tiles: dict[str, ThemeTile] = {}

        def set_selected_tile(name: str) -> None:
            nonlocal selected_palette_name
            selected_palette_name = name
            for tile_name, tile in theme_tiles.items():
                tile.set_selected(tile_name == name)
            if name in theme_tiles:
                theme_tiles[name].setFocus()

        columns = 3
        for idx, (name, pal) in enumerate(PALETTES.items()):
            tile = ThemeTile(name, pal)
            tile.clicked.connect(set_selected_tile)
            theme_tiles[name] = tile
            row, col = divmod(idx, columns)
            palette_grid.addWidget(tile, row, col)
        set_selected_tile(selected_palette_name if selected_palette_name in theme_tiles else "Slate Tide")
        palette_scroll.setWidget(palette_container)

        form = QtWidgets.QFormLayout()
        font_family = QtWidgets.QFontComboBox()
        font_family.setCurrentFont(QtGui.QFont(self.settings.get("font_family", "Segoe UI")))
        font_size = QtWidgets.QSpinBox(); font_size.setRange(8, 22); font_size.setValue(int(self.settings.get("font_size", 11)))
        font_weight = QtWidgets.QComboBox(); font_weight.addItems(["Light", "Normal", "Medium", "Bold"]); font_weight.setCurrentText(self.settings.get("font_weight", "Normal"))
        hist_width = QtWidgets.QSpinBox(); hist_width.setRange(1, 6); hist_width.setValue(int(self.settings.get("history_width", 2)))
        live_width = QtWidgets.QSpinBox(); live_width.setRange(1, 6); live_width.setValue(int(self.settings.get("live_width", 2)))

        form.addRow("Font", font_family)
        form.addRow("Font size", font_size)
        form.addRow("Font weight", font_weight)
        form.addRow("History line width", hist_width)
        form.addRow("Live line width", live_width)

        appearance_layout.addWidget(palette_scroll, 1)
        appearance_layout.addWidget(QtWidgets.QLabel("Typography & Lines"))
        appearance_layout.addLayout(form)
        tabs.addTab(appearance_tab, "Appearance")

        sources_tab = QtWidgets.QWidget()
        sources_layout = QtWidgets.QFormLayout(sources_tab)
        provider_config = self.settings.get("provider_config", {})
        twelve_cfg = provider_config.get("twelve", {})
        metals_cfg = provider_config.get("metalsapi", {})
        polygon_cfg = provider_config.get("polygon", {})

        twelve_key = QtWidgets.QLineEdit(twelve_cfg.get("api_token", ""))
        twelve_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        twelve_url = QtWidgets.QLineEdit(twelve_cfg.get("api_base_url", ""))
        metals_key = QtWidgets.QLineEdit(metals_cfg.get("api_token", ""))
        metals_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        metals_url = QtWidgets.QLineEdit(metals_cfg.get("api_base_url", ""))
        polygon_key = QtWidgets.QLineEdit(polygon_cfg.get("api_token", ""))
        polygon_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        polygon_url = QtWidgets.QLineEdit(polygon_cfg.get("api_base_url", ""))

        sources_layout.addRow("Twelve key", twelve_key)
        sources_layout.addRow("Twelve base URL", twelve_url)
        sources_layout.addRow("Metals-API key", metals_key)
        sources_layout.addRow("Metals-API base URL", metals_url)
        sources_layout.addRow("Polygon key", polygon_key)
        sources_layout.addRow("Polygon base URL", polygon_url)
        tabs.addTab(sources_tab, "Data Sources")

        quality_tab = QtWidgets.QWidget()
        quality_layout = QtWidgets.QVBoxLayout(quality_tab)
        skip_quality_checks = QtWidgets.QCheckBox("Skip quote freshness quality checks")
        skip_quality_checks.setChecked(bool(self.settings.get("skip_quality_checks", False)))
        quality_layout.addWidget(skip_quality_checks)
        quality_layout.addWidget(
            QtWidgets.QLabel("Warning: when enabled, stale quote timestamps may be accepted.")
        )
        quality_layout.addStretch(1)
        tabs.addTab(quality_tab, "Quality")

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)

        layout.addWidget(tabs, 1)
        layout.addWidget(btns)

        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.settings["palette"] = selected_palette_name
            self.settings["font_family"] = font_family.currentFont().family()
            self.settings["font_size"] = font_size.value()
            self.settings["font_weight"] = font_weight.currentText()
            self.settings["history_width"] = hist_width.value()
            self.settings["live_width"] = live_width.value()
            self.settings["skip_quality_checks"] = skip_quality_checks.isChecked()
            self.settings["provider_config"] = {
                "twelve": {
                    "api_token": twelve_key.text().strip(),
                    "api_base_url": twelve_url.text().strip(),
                },
                "metalsapi": {
                    "api_token": metals_key.text().strip(),
                    "api_base_url": metals_url.text().strip(),
                },
                "polygon": {
                    "api_token": polygon_key.text().strip(),
                    "api_base_url": polygon_url.text().strip(),
                },
            }
            self._save_settings()
            self._apply_visual_settings()
            self._refresh_provider_availability()
            self.tracker = self._make_tracker()
            self.status_label.setText("Customization saved")
            self._sync_controls_state()
            self._update_status_island(self._mode_text(), "Customization updated")

    def _make_tracker(self) -> RatioTracker:
        self._active_provider_name = self.provider_combo.currentText()
        self._active_fallback_name = self.fallback_combo.currentText()
        provider = create_provider_chain(
            self._active_provider_name,
            self._active_fallback_name,
            provider_config=self.settings.get("provider_config", {}),
        )
        return RatioTracker(
            provider=provider,
            max_points=240,
            skip_quality_checks=bool(self.settings.get("skip_quality_checks", False)),
        )

    def _on_interval_change(self, label: str) -> None:
        mapping = {"10s": 10000, "30s": 30000, "1m": 60000, "5m": 300000}
        self.timer.setInterval(mapping.get(label, 30000))
        self._save_settings()

    def _on_source_selection_changed(self, _value: str) -> None:
        self._source_dirty = True
        self._sync_controls_state()

    def _ensure_tracker_source_current(self) -> None:
        if (
            self._active_provider_name != self.provider_combo.currentText()
            or self._active_fallback_name != self.fallback_combo.currentText()
        ):
            self.tracker = self._make_tracker()
            self._source_dirty = False

    def _mode_text(self) -> str:
        return "LIVE" if self.timer.isActive() else "IDLE"

    def _format_timestamp(self, ts: dt.datetime) -> str:
        if EASTERN_TZ is not None:
            return ts.astimezone(EASTERN_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        return ts.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    def _update_status_island(self, mode: str, activity: str) -> None:
        provider = self.provider_combo.currentText()
        chart_label = {"gold": "Gold", "silver": "Silver", "ratio": "G/S"}.get(self.active_chart, "G/S")
        locks = []
        if self.lock_x_btn.isChecked():
            locks.append("X locked")
        if self.lock_y_btn.isChecked():
            locks.append("Y locked")
        if self.settings.get("skip_quality_checks", False):
            locks.append("Quality checks OFF")
        if locks:
            activity = f"{activity} ({', '.join(locks)})"
        activity = f"{activity} • {chart_label}"
        updated = self.updated_label.text()
        self.status_island.set_state(mode, provider, activity, updated)

    def apply_source(self) -> None:
        self.tracker = self._make_tracker()
        self._source_dirty = False
        msg = f"Source applied: {self.provider_combo.currentText()} / fallback: {self.fallback_combo.currentText()}"
        self.status_label.setText(msg)
        self._sync_controls_state()
        self._update_status_island(self._mode_text(), "Source changed")

    def load_history(self) -> None:
        try:
            self._busy = True
            self._sync_controls_state()
            period = self.history_combo.currentText()
            provider_name = self.provider_combo.currentText()
            context = (provider_name, period)
            if context != self.history_context:
                self.history_context = context
                self.history_store = {}
                self.chart_view_ranges = {}
            self.status_label.setText(f"Loading {period} history...")
            self._update_status_island(self._mode_text(), f"Loading {period}")
            QtWidgets.QApplication.processEvents()
            if self.active_chart in self.history_store:
                self.historical_points = self.history_store[self.active_chart]
            else:
                if self.active_chart == "gold":
                    points = load_price_history(provider_name, symbol="XAUUSD", period=period)
                elif self.active_chart == "silver":
                    points = load_price_history(provider_name, symbol="XAGUSD", period=period)
                else:
                    points = load_ratio_history(provider_name, period=period)
                self.history_store[self.active_chart] = points
                self.historical_points = points
            self._redraw()
            self.status_label.setText(
                f"Loaded {len(self.historical_points)} {self.active_chart} history points ({period})"
            )
            self._update_status_island(self._mode_text(), "History loaded")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"History load error: {exc}")
            self._update_status_island("ERROR", "History error")
        finally:
            self._busy = False
            self._sync_controls_state()

    def snapshot(self) -> None:
        try:
            self._ensure_tracker_source_current()
            snap = self.tracker.refresh()
            quality = self.tracker.last_quality_status
            self.gold_label.setText(f"{snap.gold.price:,.4f}")
            self.silver_label.setText(f"{snap.silver.price:,.4f}")
            self.ratio_label.setText(f"{snap.ratio:.6f}")
            self.updated_label.setText(self._format_timestamp(snap.timestamp))
            self._refresh_live_points_from_tracker()
            self._redraw()
            self.status_label.setText(
                f"Snapshot updated • {quality.activity_label} via {quality.provider_used}"
                + (f" ({quality.detail})" if quality.detail else "")
            )
            self._update_status_island(self._mode_text(), quality.activity_label)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Snapshot error: {exc}")
            quality = self.tracker.last_quality_status
            activity = quality.activity_label if quality.state == "stale_pair" else "Snapshot error"
            self._update_status_island("ERROR", activity)

    def start_live(self) -> None:
        self.timer.start()
        self.snapshot()
        self.status_label.setText("Live updates running")
        self._sync_controls_state()
        self._update_status_island("LIVE", f"Every {self.interval_combo.currentText()}")

    def pause_live(self) -> None:
        self.timer.stop()
        self.status_label.setText("Live updates paused")
        self._sync_controls_state()
        self._update_status_island("PAUSED", "Updates paused")

    def terminate_session(self) -> None:
        self.timer.stop()
        self.tracker.history.clear()
        self.historical_points = []
        self.live_points = []
        for lbl in [self.gold_label, self.silver_label, self.ratio_label, self.updated_label]:
            lbl.setText("-")
        self._redraw()
        self.status_label.setText("Session terminated")
        self._sync_controls_state()
        self._update_status_island("TERMINATED", "Cleared")

    def _show_plot_menu(self, pos: QtCore.QPoint) -> None:
        menu = LiquidGlassMenu(self, profile_name="floating_menu")
        menu.set_surface_colors(
            self._active_palette["surface"],
            self._active_palette["grid"],
            self._active_palette["accent"],
        )
        fit_action = menu.addAction("Fit to data")
        fit_action.triggered.connect(self._fit_chart)

        toggle_grid_action = menu.addAction("Toggle grid")
        toggle_grid_action.triggered.connect(self._toggle_grid)
        toggle_legend_action = menu.addAction("Toggle legend")
        toggle_legend_action.triggered.connect(self._toggle_legend)

        menu.addSeparator()
        lock_x_action = menu.addAction("Toggle X lock")
        lock_x_action.triggered.connect(lambda: self.lock_x_btn.setChecked(not self.lock_x_btn.isChecked()))
        lock_y_action = menu.addAction("Toggle Y lock")
        lock_y_action.triggered.connect(lambda: self.lock_y_btn.setChecked(not self.lock_y_btn.isChecked()))

        menu.addSeparator()
        clear_live_action = menu.addAction("Clear live points")
        clear_live_action.triggered.connect(self._clear_live_points)

        anchor = QtGui.QCursor.pos()
        left_margin, top_margin, _, _ = menu._popup_halo_margins()
        base_anchor = QtCore.QPoint(anchor.x() - left_margin, anchor.y() - top_margin)
        final_anchor = self._clamp_popup_anchor(menu, base_anchor)
        menu.exec(final_anchor)

    def _clamp_popup_anchor(self, menu: QtWidgets.QMenu, anchor: QtCore.QPoint) -> QtCore.QPoint:
        screen = QtGui.QGuiApplication.screenAt(anchor) or QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            return anchor
        available = screen.availableGeometry()
        menu_size = menu.sizeHint()
        x = min(max(anchor.x(), available.left()), max(available.left(), available.right() - menu_size.width()))
        y = min(max(anchor.y(), available.top()), max(available.top(), available.bottom() - menu_size.height()))
        return QtCore.QPoint(x, y)

    def _clear_live_points(self) -> None:
        self.live_points = []
        self.tracker.history.clear()
        self._redraw()
        self.status_label.setText("Live points cleared")

    def _set_active_chart(self, chart_key: str) -> None:
        self.active_chart = chart_key
        for key, card in self.chart_cards.items():
            card.set_selected(key == chart_key)
        self._apply_chart_axis_labels()
        if self.active_chart in self.history_store:
            self.historical_points = self.history_store[self.active_chart]
        else:
            self.historical_points = []
        self._refresh_live_points_from_tracker()
        self._redraw()
        vb = self.plot_widget.getViewBox()
        saved = self.chart_view_ranges.get(chart_key)
        if saved is None:
            self._fit_chart()
        else:
            x_range, y_range = saved
            vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
            vb.setXRange(x_range[0], x_range[1], padding=0)
            vb.setYRange(y_range[0], y_range[1], padding=0)
        self._update_status_island(self._mode_text(), "Chart selected")

    def _apply_chart_axis_labels(self) -> None:
        left_label = "G/S"
        if self.active_chart == "gold":
            left_label = "Gold (USD/oz)"
        elif self.active_chart == "silver":
            left_label = "Silver (USD/oz)"
        self.plot_widget.setLabel("left", left_label)
        self.plot_widget.setLabel("bottom", "Time")

    def _refresh_live_points_from_tracker(self) -> None:
        if self.active_chart == "gold":
            self.live_points = [(s.timestamp, s.gold.price) for s in self.tracker.history]
        elif self.active_chart == "silver":
            self.live_points = [(s.timestamp, s.silver.price) for s in self.tracker.history]
        else:
            self.live_points = [(s.timestamp, s.ratio) for s in self.tracker.history]

    def _toggle_grid(self) -> None:
        self._grid_visible = not self._grid_visible
        self.plot_widget.showGrid(x=self._grid_visible, y=self._grid_visible, alpha=0.25 if self._grid_visible else 0.0)

    def _toggle_legend(self) -> None:
        if self.legend is None:
            return
        self.legend.setVisible(not self.legend.isVisible())

    def _fit_chart(self) -> None:
        self.plot_widget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        vb = self.plot_widget.getViewBox()
        x_range, y_range = vb.viewRange()
        self.chart_view_ranges[self.active_chart] = (x_range, y_range)

    def _clamp_range(
        self,
        lo: float,
        hi: float,
        min_allowed: float,
        max_allowed: float,
        *,
        min_span: float,
        max_span: float,
    ) -> tuple[float, float]:
        if max_allowed <= min_allowed:
            max_allowed = min_allowed + max(min_span, 1.0)
        span = hi - lo
        default_span = max(min_span, min(max_span, (max_allowed - min_allowed) * 0.2))
        if span <= 0:
            span = default_span
        span = max(min_span, min(span, max_span))

        lo = max(lo, min_allowed)
        hi = min(hi, max_allowed)
        if hi - lo < min_span:
            center = (lo + hi) / 2
            lo = center - span / 2
            hi = center + span / 2
        if hi - lo > max_span:
            center = (lo + hi) / 2
            lo = center - max_span / 2
            hi = center + max_span / 2

        lo = max(lo, min_allowed)
        hi = min(hi, max_allowed)
        if hi - lo < min_span:
            hi = min(lo + min_span, max_allowed)
            lo = max(hi - min_span, min_allowed)
        return lo, hi

    def _compute_plot_bounds(self) -> tuple[float, float, float, float] | None:
        hist_x = [p[0].timestamp() for p in self.historical_points]
        hist_y = [p[1] for p in self.historical_points]
        live_x = [p[0].timestamp() for p in self.live_points]
        live_y = [p[1] for p in self.live_points]
        all_x = hist_x + live_x
        all_y = hist_y + live_y
        if not all_x or not all_y:
            return None

        x_min = min(all_x)
        x_max_data = max(all_x)
        x_span = max(x_max_data - x_min, 60.0)
        x_pad = max(60.0, x_span * 0.02)
        x_max = x_max_data + x_pad

        y_min_data = max(min(all_y), 0.0001)
        y_max_data = max(all_y)
        y_span = max(y_max_data - y_min_data, 0.5)
        y_pad = max(0.25, y_span * 0.2)
        y_min = max(0.0001, y_min_data - y_pad)
        y_max = y_max_data + y_pad
        return x_min, x_max, y_min, y_max

    def _enforce_bounds(self, source: str) -> None:
        bounds = self._compute_plot_bounds()
        if bounds is None:
            return
        x_min, x_max, y_min, y_max = bounds

        vb = self.plot_widget.getViewBox()
        prev_x, prev_y = vb.viewRange()
        x_span_data = max(x_max - x_min, 60.0)
        y_span_data = max(y_max - y_min, 1.0)

        if not self.lock_x_btn.isChecked() and not self.lock_y_btn.isChecked():
            if source == "update":
                vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
            return

        vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
        self._applying_bounds = True
        try:
            if self.lock_x_btn.isChecked():
                x_lo, x_hi = self._clamp_range(
                    prev_x[0],
                    prev_x[1],
                    x_min,
                    x_max,
                    min_span=60.0,
                    max_span=max(60.0, x_span_data * 1.2),
                )
                vb.setXRange(x_lo, x_hi, padding=0)
            elif source == "update":
                vb.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)

            if self.lock_y_btn.isChecked():
                y_lo, y_hi = self._clamp_range(
                    prev_y[0],
                    prev_y[1],
                    y_min,
                    y_max,
                    min_span=0.1,
                    max_span=max(0.5, y_span_data * 1.5),
                )
                vb.setYRange(y_lo, y_hi, padding=0)
            elif source == "update":
                vb.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        finally:
            self._applying_bounds = False

    def _on_range_changed(self, _view_box, _ranges) -> None:
        if self._applying_bounds:
            return
        vb = self.plot_widget.getViewBox()
        x_range, y_range = vb.viewRange()
        self.chart_view_ranges[self.active_chart] = (x_range, y_range)
        self._enforce_bounds(source="user")

    def _redraw(self) -> None:
        hist_x = [p[0].timestamp() for p in self.historical_points]
        hist_y = [p[1] for p in self.historical_points]
        live_x = [p[0].timestamp() for p in self.live_points]
        live_y = [p[1] for p in self.live_points]

        self.hist_curve.setData(hist_x, hist_y)
        self.live_curve.setData(live_x, live_y)

        self._enforce_bounds(source="update")


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    win = TrackerWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
