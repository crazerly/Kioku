import time
import json
from datetime import datetime

from __init__ import convert_date

try:
    from PySide6.QtWidgets import (
        QHBoxLayout, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QDialog,
        QHeaderView, QMenu, QLabel, QMessageBox, QDialogButtonBox,
        QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
        QDateTimeEdit, QGroupBox, QFormLayout, QLineEdit, QTextEdit
    )
    from PySide6.QtCore import Qt, QDateTime
    from PySide6.QtGui import QAction, QIcon
    QT_BACKEND = "PySide6"
except Exception:
    from PyQt5.QtWidgets import (
        QHBoxLayout, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QDialog,
        QHeaderView, QMenu, QLabel, QMessageBox, QDialogButtonBox,
        QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
        QDateTimeEdit
    )
    from PyQt5.QtCore import Qt, QDateTime
    from PyQt5.QtGui import QAction, QIcon
    QT_BACKEND = "PyQt5"

class BrowseWindow(QDialog):
    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browse Cards")
        self.resize(1000, 600)
        self.setWindowIcon(QIcon('icon\\lightbulb.ico'))
        self.db_conn = db_conn

        self.selected_deck_id = None # None = Collection
        self.selected_state = "All"
        self.selected_tag = None

        self._build_ui()
        self._load_decks()
        self._load_tags()
        self.load_cards()

    def _build_ui(self):
        root = QHBoxLayout(self)

        # Decks
        sidebar = QVBoxLayout()
        sidebar.addWidget(QLabel("<b>Decks</b>"))
        self.deck_tree = QTreeWidget()
        self.deck_tree.setHeaderHidden(True)
        self.deck_tree.itemSelectionChanged.connect(self.on_deck_selection_changed)
        sidebar.addWidget(self.deck_tree, stretch=2)

        # Card State
        sidebar.addWidget(QLabel("<b>Card State</b>"))
        self.state_list = QListWidget()
        for card_state in ["All", "New", "Learn", "Review"]:
            item = QListWidgetItem(card_state)
            self.state_list.addItem(item)
        self.state_list.setCurrentRow(0)
        self.state_list.currentItemChanged.connect(self.on_state_changed)
        sidebar.addWidget(self.state_list, stretch=0)

        # Tags
        sidebar.addWidget(QLabel("<b>Tags</b>"))
        self.tags_list = QListWidget()
        self.tags_list.itemClicked.connect(self.on_tag_changed)
        sidebar.addWidget(self.tags_list, stretch=1)

        root.addLayout(sidebar, stretch=30)

        # Cards table
        layout = QVBoxLayout()
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("<b>Cards</b>"))
        layout.addLayout(header_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Due", "Card Type", "Deck", "Front preview", "ID"])
        self.table.setColumnHidden(4, True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)

        layout.addWidget(self.table)
        root.addLayout(layout, stretch=70)

    def _load_decks(self):
        cur = self.db_conn.cursor()
        cur.execute("SELECT id, name, parent_deck_id FROM decks")
        rows = cur.fetchall()
        decks = [dict(row) for row in rows]
        
        by_id = {deck["id"]: deck for deck in decks}
        children = {}
        for deck in decks:
            pid = deck["parent_deck_id"]
            children.setdefault(pid, []).append(deck["id"])

        self.deck_tree.clear()
        
        root_item = QTreeWidgetItem(self.deck_tree, ["Collection"])
        root_item.setData(0, Qt.UserRole, None)
        root_item.setExpanded(True)

        def add_children(parent_item, parent_id):
            for cid in sorted(children.get(parent_id, []), key=lambda i: by_id[i]["name"]):
                deck = by_id[cid]
                it = QTreeWidgetItem(parent_item, [deck["name"]])
                it.setData(0, Qt.UserRole, deck["id"])
                it.setExpanded(True)
                add_children(it, deck["id"])

        add_children(root_item, None)
        self.deck_tree.setCurrentItem(root_item)

    def on_deck_selection_changed(self):
        items = self.deck_tree.selectedItems()
        if not items:
            self.selected_deck_id = None
        else:
            self.selected_deck_id = items[0].data(0, Qt.UserRole)
        self.load_cards()

    def _load_tags(self):
        cur = self.db_conn.cursor()
        cur.execute("SELECT tags FROM cards WHERE tags IS NOT NULL AND tags != ''")
        rows = cur.fetchall()
        tagset = set()
        for row in rows:
            raw = row["tags"]
            if not raw:
                continue
            for t in raw.split(","):
                tag = t.strip()
                if tag:
                    tagset.add(tag)
        self.tags_list.clear()
        for tag in sorted(tagset):
            it = QListWidgetItem(tag)
            self.tags_list.addItem(it)

    def on_tag_changed(self, item):
        if self.selected_tag == item.text():
            self.tags_list.clearSelection()
            self.selected_tag = None
        else:
            self.selected_tag = item.text()
        self.load_cards()

    def on_state_changed(self, cur, prev=None):
        if cur:
            self.selected_state = cur.text()
        else:
            self.selected_state = "All"
        self.load_cards()

    def _get_deck_subtree_ids(self, root_deck_id):
        cur = self.db_conn.cursor()
        cur.execute("SELECT id, parent_deck_id FROM decks")
        rows = cur.fetchall()
        children = {}
        for row in rows:
            pid = row["parent_deck_id"]
            children.setdefault(pid, []).append(row["id"])

        result = []
        if root_deck_id is None:
            return [row["id"] for row in rows]

        stack = [root_deck_id]
        while stack:
            deck = stack.pop()
            result.append(deck)
            for child in children.get(deck, []):
                stack.append(child)
        return result

    def load_cards(self):
        now = int(time.time())
        deck_ids = None
        if self.selected_deck_id is None:
            deck_ids = self._get_deck_subtree_ids(None)
        else:
            deck_ids = self._get_deck_subtree_ids(self.selected_deck_id)
        deck_placeholder = ",".join(["?"] * len(deck_ids)) if deck_ids else "NULL"
        params = []
        params.extend(deck_ids)

        state_clause = ""
        if self.selected_state == "New":
            state_clause = "AND (cards.reps = 0 AND IFNULL(cards.learning_step_index, 0) = 0 AND cards.next_due IS NULL)"
        elif self.selected_state == "Learn":
            state_clause = "AND (cards.reps = 0 AND (IFNULL(cards.learning_step_index,0) > 0 OR cards.next_due IS NOT NULL))"
        elif self.selected_state == "Review":
            state_clause = "AND (cards.next_due IS NOT NULL AND cards.next_due <= ?)"
            params.append(now)
        else:
            state_clause = ""

        tag_clause = ""
        if self.selected_tag:
            tag_clause = "AND (cards.tags IS NOT NULL AND cards.tags LIKE ?)"
            params.append(f"%{self.selected_tag}%")

        sql = f"""
            SELECT cards.id AS card_id,
                   cards.fields AS fields_json,
                   cards.next_due AS next_due,
                   cards.template_front AS template_front,
                   cards.template_back AS template_back,
                   card_types.id AS card_type_id,
                   card_types.name AS card_type_name,
                   card_types.fields AS card_type_fields,
                   decks.id AS deck_id,
                   decks.name AS deck_name,
                   cards.reps, cards.interval, cards.ease, cards.learning_step_index, cards.last_reviewed
            FROM cards
            LEFT JOIN card_types ON cards.card_type_id = card_types.id
            LEFT JOIN decks ON cards.deck_id = decks.id
            WHERE cards.is_active = 1
              AND cards.deck_id IN ({deck_placeholder})
              {state_clause}
              {tag_clause}
            ORDER BY
              CASE WHEN cards.next_due IS NULL THEN 1 ELSE 0 END, cards.next_due ASC, cards.id ASC
        """

        cur = self.db_conn.cursor()
        try:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
        except Exception as e:
            print("SQL error:", e)
            rows = []

        self.table.setRowCount(0)
        for row in rows:
            row_dict = dict(row)
            row_id = row_dict["card_id"]
            fields_json = row_dict.get("fields_json") or "{}"
            try:
                fields = json.loads(fields_json)
            except Exception:
                fields = {}
            preview = ""
            if isinstance(fields, dict) and fields:
                first_key = next(iter(fields.keys()))
                preview = str(fields.get(first_key, ""))[:200]
            elif isinstance(fields, (list, tuple)) and fields:
                preview = str(fields[0])[:200]

            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            due_str = convert_date(row_dict.get("next_due"))
            self.table.setItem(row_idx, 0, QTableWidgetItem(due_str))
            self.table.setItem(row_idx, 1, QTableWidgetItem(row_dict.get("card_type_name") or ""))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row_dict.get("deck_name") or ""))
            self.table.setItem(row_idx, 3, QTableWidgetItem(preview))
            id_item = QTableWidgetItem(str(row_id))
            id_item.setData(Qt.UserRole, row_id)
            self.table.setItem(row_idx, 4, id_item)

            tooltip = f"reps={row_dict.get('reps')}, interval={row_dict.get('interval')}, ease={row_dict.get('ease')}, learning_index={row_dict.get('learning_step_index')}, last_reviewed={convert_date(row_dict.get('last_reviewed'))}"
            for c in range(4):
                it = self.table.item(row_idx, c)
                if it:
                    it.setToolTip(tooltip)

    def on_table_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        card_id_item = self.table.item(row, 4)
        if not card_id_item:
            return
        card_id = card_id_item.data(Qt.UserRole)

        menu = QMenu(self)
        edit_act = QAction("Edit", self)
        change_due_act = QAction("Change due date", self)
        delete_act = QAction("Delete", self)
        menu.addAction(edit_act)
        menu.addAction(change_due_act)
        menu.addAction(delete_act)

        edit_act.triggered.connect(lambda: self._edit_card(card_id))
        change_due_act.triggered.connect(lambda: self._change_due(card_id))
        delete_act.triggered.connect(lambda: self._delete_card(card_id))

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _fetch_card_row(self, card_id):
        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT cards.id AS card_id, cards.fields AS fields_json, cards.template_front, cards.template_back,
                   card_types.id AS card_type_id, card_types.fields AS card_type_fields, card_types.name AS card_type_name
            FROM cards
            LEFT JOIN card_types ON cards.card_type_id = card_types.id
            WHERE cards.id = ?
        """, (card_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def _edit_card(self, card_id):
        card_row = self._fetch_card_row(card_id)
        if not card_row:
            QMessageBox.warning(self, "Edit card", f"Card {card_id} not found.")
            return

        try:
            fields = json.loads(card_row.get("fields_json") or "{}")
        except Exception:
            fields = {}

        try:
            card_type_fields = json.loads(card_row.get("card_type_fields") or "[]")
        except Exception:
            card_type_fields = []

        card_obj = {
            "id": card_row["card_id"],
            "card_type_id": card_row["card_type_id"],
            "fields": fields,
            "template_front": card_row.get("template_front"),
            "template_back": card_row.get("template_back"),
            "card_type_fields": card_type_fields
        }

        dialog = EditCardDialog(card_obj, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        fields_new, tpl_front_new, tpl_back_new = dialog.get_result()

        cur = self.db_conn.cursor()
        cur.execute("""
            UPDATE cards
               SET fields = ?, template_front = ?, template_back = ?
             WHERE id = ?
        """, (json.dumps(fields_new, ensure_ascii=False), tpl_front_new, tpl_back_new, card_id))
        self.db_conn.commit()
        self.load_cards()

    def _change_due(self, card_id):
        cur = self.db_conn.cursor()
        cur.execute("SELECT next_due FROM cards WHERE id = ?", (card_id,))
        row = cur.fetchone()
        cur_due = row["next_due"] if row else None
        dialog = QDialog(self)
        dialog.setWindowTitle("Change due date")
        layout = QVBoxLayout(dialog)

        date_time = QDateTimeEdit(dialog)
        if cur_due:
            date_time.setDateTime(QDateTime.fromSecsSinceEpoch(int(cur_due)))
        else:
            date_time.slgetDateTime(QDateTime.currentDateTime())
        layout.addWidget(QLabel("Choose new due date and time:"))
        layout.addWidget(date_time)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() != QDialog.Accepted:
            return

        new_time = int(date_time.dateTime().toSecsSinceEpoch())
        if new_time < datetime.now().timestamp():
            QMessageBox.warning(self, "Invalid Due Time", "Next due time cannot be set to the past.", 
            QMessageBox.Ok | QMessageBox.No,
            QMessageBox.No)
            return
        cur = self.db_conn.cursor()
        cur.execute("UPDATE cards SET next_due = ? WHERE id = ?", (new_time, card_id))
        self.db_conn.commit()
        self.load_cards()

    def _delete_card(self, card_id):
        ok = QMessageBox.question(self,
            "Delete card",
            f"Are you sure you want to delete this card?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return
        cur = self.db_conn.cursor()
        
        cur.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        self.db_conn.commit()
        self.load_cards()

class EditCardDialog(QDialog):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Card")
        self.resize(700, 500)
        self.card = card

        layout = QVBoxLayout(self)

        fields_group = QGroupBox("Fields")
        field_layout = QFormLayout(fields_group)
        self.field_widgets = {}
        for fname in card.get("card_type_fields", []):
            line_edit = QLineEdit()
            value = card.get("fields", {}).get(fname, "")
            line_edit.setText(value)
            field_layout.addRow(f"{fname}:", line_edit)
            self.field_widgets[fname] = line_edit
        layout.addWidget(fields_group, stretch=1)

        template_group = QGroupBox("Templates")
        template_layout = QVBoxLayout(template_group)
        template_layout.addWidget(QLabel("Front template:"))
        self.front_edit = QTextEdit()
        self.front_edit.setPlainText(card.get("template_front", "") or "")
        template_layout.addWidget(self.front_edit, 1)
        template_layout.addWidget(QLabel("Back template:"))
        self.back_edit = QTextEdit()
        self.back_edit.setPlainText(card.get("template_back", "") or "")
        template_layout.addWidget(self.back_edit, 1)
        layout.addWidget(template_group, stretch=2)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_result(self):
        fields = {fname: w.text() for fname, w in self.field_widgets.items()}
        return fields, self.front_edit.toPlainText(), self.back_edit.toPlainText()
