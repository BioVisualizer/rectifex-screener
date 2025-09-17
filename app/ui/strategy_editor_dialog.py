import copy
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                             QPushButton, QGroupBox, QFormLayout, QLineEdit,
                             QSpinBox, QDialogButtonBox, QMessageBox, QWidget)

class StrategyEditorDialog(QDialog):
    def __init__(self, strategies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Strategy Editor")
        self.setMinimumSize(700, 500)

        self.strategies = copy.deepcopy(strategies)
        self.current_strategy_name = None
        self.score_keys = ["Quality_Score", "Value_Score", "Growth_Score", "Momentum_Score", "Yield_Score", "Safety_Score"]

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        editor_layout = QHBoxLayout()
        main_layout.addLayout(editor_layout)

        # --- Left Panel: Strategy List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Strategies:"))
        self.strategy_list_widget = QListWidget()
        left_layout.addWidget(self.strategy_list_widget)

        list_button_layout = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.copy_button = QPushButton("Copy")
        self.delete_button = QPushButton("Delete")
        list_button_layout.addWidget(self.new_button)
        list_button_layout.addWidget(self.copy_button)
        list_button_layout.addWidget(self.delete_button)
        left_layout.addLayout(list_button_layout)
        editor_layout.addWidget(left_panel, 1)

        # --- Right Panel: Editor ---
        self.editor_groupbox = QGroupBox("Edit Strategy")
        self.editor_groupbox.setEnabled(False)
        form_layout = QFormLayout(self.editor_groupbox)

        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)

        self.score_spinboxes = {}
        for key in self.score_keys:
            spinbox = QSpinBox()
            spinbox.setRange(0, 100)
            spinbox.setSuffix("%")
            spinbox.valueChanged.connect(self.update_weight_sum)
            self.score_spinboxes[key] = spinbox
            form_layout.addRow(key.replace('_', ' ') + ":", spinbox)

        self.sum_label = QLabel("Total: 0%")
        self.sum_label.setStyleSheet("font-weight: bold;")
        form_layout.addRow(self.sum_label)
        editor_layout.addWidget(self.editor_groupbox, 2)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        # --- Connections & Initial State ---
        self.strategy_list_widget.itemSelectionChanged.connect(self.on_strategy_selection_changed)
        self.name_input.textChanged.connect(self.on_name_changed)
        self.new_button.clicked.connect(self.new_strategy)
        self.copy_button.clicked.connect(self.copy_strategy)
        self.delete_button.clicked.connect(self.delete_strategy)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)

        self.populate_strategy_list()

    def populate_strategy_list(self, select_name=None):
        self.strategy_list_widget.blockSignals(True)
        self.strategy_list_widget.clear()
        for name in sorted(self.strategies.keys()):
            self.strategy_list_widget.addItem(name)
            if name == select_name:
                self.strategy_list_widget.setCurrentRow(self.strategy_list_widget.count() - 1)
        self.strategy_list_widget.blockSignals(False)
        if self.strategy_list_widget.currentItem():
            self.on_strategy_selection_changed()
        else:
            self.editor_groupbox.setEnabled(False)


    def on_strategy_selection_changed(self):
        selected_items = self.strategy_list_widget.selectedItems()
        if not selected_items:
            self.current_strategy_name = None
            self.editor_groupbox.setEnabled(False)
            return

        new_name = selected_items[0].text()
        if self.current_strategy_name and self.current_strategy_name != new_name:
            self.save_current_editor_state()

        self.current_strategy_name = new_name
        self.load_strategy_into_editor()

    def load_strategy_into_editor(self):
        if not self.current_strategy_name: return

        strategy_data = self.strategies[self.current_strategy_name]
        is_predefined = strategy_data.get("predefined", False)

        self.name_input.setText(self.current_strategy_name)
        self.name_input.setReadOnly(is_predefined)
        self.delete_button.setEnabled(not is_predefined)
        self.editor_groupbox.setEnabled(True)

        for key, spinbox in self.score_spinboxes.items():
            spinbox.blockSignals(True)
            spinbox.setValue(int(strategy_data.get("weights", {}).get(key, 0) * 100))
            spinbox.blockSignals(False)

        self.update_weight_sum()

    def save_current_editor_state(self):
        if not self.current_strategy_name: return

        old_name = self.current_strategy_name
        new_name = self.name_input.text()

        if not new_name:
             # User cleared the name field, revert to old name to avoid issues
            self.name_input.setText(old_name)
            new_name = old_name

        strategy_data = self.strategies.pop(old_name)
        strategy_data["weights"] = {key: spinbox.value() / 100.0 for key, spinbox in self.score_spinboxes.items()}
        self.strategies[new_name] = strategy_data
        self.current_strategy_name = new_name


    def on_name_changed(self, new_name):
        if not self.current_strategy_name: return

        selected_items = self.strategy_list_widget.selectedItems()
        if not selected_items: return

        # Prevent renaming to an existing name
        if new_name != self.current_strategy_name and new_name in self.strategies:
            self.name_input.setStyleSheet("color: red;")
        else:
            self.name_input.setStyleSheet("")

        selected_items[0].setText(new_name)


    def update_weight_sum(self):
        total_weight = sum(spinbox.value() for spinbox in self.score_spinboxes.values())
        self.sum_label.setText(f"Total: {total_weight}%")
        if total_weight != 100:
            self.sum_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.sum_label.setStyleSheet("color: green; font-weight: bold;")

    def new_strategy(self):
        self.save_current_editor_state()
        base_name = "New Strategy"
        name = base_name
        i = 1
        while name in self.strategies:
            name = f"{base_name} {i}"
            i += 1

        self.strategies[name] = {"weights": {key: 0 for key in self.score_keys}, "predefined": False}
        self.populate_strategy_list(select_name=name)

    def copy_strategy(self):
        if not self.current_strategy_name: return
        self.save_current_editor_state()

        base_name = f"{self.current_strategy_name} (Copy)"
        name = base_name
        i = 1
        while name in self.strategies:
            name = f"{base_name} {i}"
            i += 1

        original_strategy = self.strategies[self.current_strategy_name]
        self.strategies[name] = {
            "weights": original_strategy["weights"].copy(),
            "predefined": False
        }
        self.populate_strategy_list(select_name=name)

    def delete_strategy(self):
        if not self.current_strategy_name or self.strategies[self.current_strategy_name].get("predefined", False):
            return

        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete '{self.current_strategy_name}'?")
        if reply == QMessageBox.Yes:
            del self.strategies[self.current_strategy_name]
            self.current_strategy_name = None
            self.populate_strategy_list()

    def on_accept(self):
        self.save_current_editor_state()

        invalid_strategies = []
        for name, data in self.strategies.items():
            total_weight = sum(data.get("weights", {}).values())
            if not (0.999 < total_weight < 1.001):
                invalid_strategies.append(name)

        if invalid_strategies:
            QMessageBox.warning(self, "Invalid Weights", "The following strategies do not have weights summing to 100%:\n\n" + "\n".join(invalid_strategies))
            return

        # Check for duplicate names
        if len(self.strategies.keys()) != len(set(self.strategies.keys())):
             QMessageBox.warning(self, "Duplicate Names", "Strategy names must be unique.")
             return

        self.accept()

    def get_updated_strategies(self):
        return self.strategies
