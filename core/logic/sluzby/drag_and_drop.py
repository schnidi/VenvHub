#----------------------------------------
# Súbor: core/logic/sluzby/drag_and_drop.py
#----------------------------------------

from PyQt6.QtWidgets import QTableWidget, QAbstractItemView
from PyQt6.QtCore import pyqtSignal

class AdvancedDragDropTable(QTableWidget):
    """
    Nezničiteľná tabuľka pre Drag and Drop.
    VYUŽÍVA 3-ZÓNOVÝ MODEL:
    - Vrchných/Ľavých 25% bunky = Vloží pred ňu (Insert)
    - Stredných 50% bunky = Vymení ich pozície (Swap)
    - Spodných/Pravých 25% bunky = Vloží za ňu (Insert)
    """
    
    order_changed = pyqtSignal()

    def __init__(self, parent=None, orientation="vertical"):
        super().__init__(parent)
        self.orientation = orientation
        
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        if self.orientation == "vertical":
            self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        else:
            self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectColumns)

    def dropEvent(self, event):
        if event.source() != self:
            super().dropEvent(event)
            return

        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        
        # Nastavenie citlivosti zón (0.25 = 25% od okraja pre vloženie, zvyšok je výmena)
        MARGIN_RATIO = 0.25 

        # ==========================================
        # VETVA 1: VERTIKÁLNY PRESUN (RIADKY)
        # ==========================================
        if self.orientation == "vertical":
            source_row = self.currentRow()
            if source_row < 0:
                event.ignore()
                return

            target_row = target_item.row() if target_item else self.rowCount()
            
            action = 'insert'
            insert_idx = target_row

            # 1. Výpočet 3 zón
            if target_item:
                rect = self.visualRect(self.indexFromItem(target_item))
                top_bound = rect.top() + rect.height() * MARGIN_RATIO
                bottom_bound = rect.bottom() - rect.height() * MARGIN_RATIO

                if pos.y() < top_bound:
                    action = 'insert'
                    insert_idx = target_row
                elif pos.y() > bottom_bound:
                    action = 'insert'
                    insert_idx = target_row + 1
                else:
                    action = 'swap'
            else:
                insert_idx = self.rowCount()

            # 2. Rýchla kontrola, či vôbec niečo meníme (zabraňuje zbytočnému prekresľovaniu)
            if action == 'swap' and source_row == target_row:
                event.ignore()
                return
                
            if action == 'insert':
                # Korekcia indexu: ak vkladáme ZA pôvodné miesto, pole sa zmenší o 1 vymazaním
                if insert_idx > source_row:
                    insert_idx -= 1
                if source_row == insert_idx:
                    event.ignore()
                    return

            # --- 3. VYTIAHNUTIE DÁT DO PAMÄTE ---
            all_rows = []
            for r in range(self.rowCount()):
                row_data = []
                for c in range(self.columnCount()):
                    row_data.append(self.takeItem(r, c))
                all_rows.append(row_data)

            # --- 4. ZORADENIE V PYTHONE ---
            if action == 'swap':
                # Doslova si vymenia miesta v zozname
                all_rows[source_row], all_rows[target_row] = all_rows[target_row], all_rows[source_row]
                final_row = target_row
            else: # action == 'insert'
                # Vytiahne sa zo starého a vloží na nové
                moved_row = all_rows.pop(source_row)
                all_rows.insert(insert_idx, moved_row)
                final_row = insert_idx

            # --- 5. VLOŽENIE SPÄŤ ---
            for r, row_data in enumerate(all_rows):
                for c, item in enumerate(row_data):
                    if item:
                        self.setItem(r, c, item)

            # --- 6. BEZPEČNÉ UKONČENIE ---
            event.ignore()
            self.selectRow(final_row)
            self.order_changed.emit()

        # ==========================================
        # VETVA 2: HORIZONTÁLNY PRESUN (STĹPCE)
        # ==========================================
        elif self.orientation == "horizontal":
            source_col = self.currentColumn()
            if source_col < 0:
                event.ignore()
                return

            target_col = target_item.column() if target_item else self.columnCount()
            
            action = 'insert'
            insert_idx = target_col

            # 1. Výpočet 3 zón
            if target_item:
                rect = self.visualRect(self.indexFromItem(target_item))
                left_bound = rect.left() + rect.width() * MARGIN_RATIO
                right_bound = rect.right() - rect.width() * MARGIN_RATIO

                if pos.x() < left_bound:
                    action = 'insert'
                    insert_idx = target_col
                elif pos.x() > right_bound:
                    action = 'insert'
                    insert_idx = target_col + 1
                else:
                    action = 'swap'
            else:
                insert_idx = self.columnCount()

            # 2. Rýchla kontrola
            if action == 'swap' and source_col == target_col:
                event.ignore()
                return
                
            if action == 'insert':
                if insert_idx > source_col:
                    insert_idx -= 1
                if source_col == insert_idx:
                    event.ignore()
                    return

            # --- 3. VYTIAHNUTIE DÁT DO PAMÄTE ---
            all_cols = []
            for c in range(self.columnCount()):
                col_data = []
                for r in range(self.rowCount()):
                    col_data.append(self.takeItem(r, c))
                all_cols.append(col_data)

            # --- 4. ZORADENIE V PYTHONE ---
            if action == 'swap':
                all_cols[source_col], all_cols[target_col] = all_cols[target_col], all_cols[source_col]
                final_col = target_col
            else:
                moved_col = all_cols.pop(source_col)
                all_cols.insert(insert_idx, moved_col)
                final_col = insert_idx

            # --- 5. VLOŽENIE SPÄŤ ---
            for c, col_data in enumerate(all_cols):
                for r, item in enumerate(col_data):
                    if item:
                        self.setItem(r, c, item)

            # --- 6. BEZPEČNÉ UKONČENIE ---
            event.ignore()
            self.selectColumn(final_col)
            self.order_changed.emit()