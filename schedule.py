import pandas as pd
import json
from collections import defaultdict

from utils import is_valid_teacher


class TeacherSchedule:
    def __init__(self, excel_path, data_start_row=5):
        self.df = pd.read_excel(excel_path, header=[0, 1])
        self.df = self.df.iloc[data_start_row:].copy()
        self.fach_std_translate = {
            "Fach": "Fach",
            "5std LF": "Fach",
            "3std BF": "Fach",
            "2std BF": "Fach",
            "Std": "Std",
        }

        self._clean_headers()
        self._normalize_headers()
        self._remove_non_teacher_rows()
        self.teaching_loads = self._extract_teacher_meta()
        self._remove_non_class_columns()
        self._standardize_columns()
        self.class_columns = self._extract_class_columns()
        print("class columns:\n", self.class_columns)

    def _clean_headers(self):
        # Drop columns where BOTH the main header and subheader are blank or NaN
        self.df = self.df.loc[
            :,
            ~(
                (
                    self.df.columns.get_level_values(0).isna()
                    | (self.df.columns.get_level_values(0) == "")
                )
                & (
                    self.df.columns.get_level_values(1).isna()
                    | (self.df.columns.get_level_values(1) == "")
                )
            ),
        ]
        # Drop columns where subheader is 'Std.1'
        self.df = self.df.loc[
            :, ~self.df.columns.get_level_values(1).str.contains(r"^Std\.\d+$")
        ]

        seen = defaultdict(list)

        for col in self.df.columns:
            first, second = col
            if isinstance(second, str) and second.startswith("Unnamed:"):
                seen[first].append(col)

        # Step 2: For each group, drop all except the first one
        to_drop = []
        for cols in seen.values():
            if len(cols) > 1:
                to_drop.extend(cols[1:])  # keep first, drop rest

        # Step 3: Drop columns
        self.df = self.df.drop(columns=to_drop)

        # Rename first column to ('Lehrer', '')
        columns = list(self.df.columns)
        columns[0] = ("Lehrer", "")
        self.df.columns = pd.MultiIndex.from_tuples(columns)
        self.df = self.df.set_index(("Lehrer", ""))

    def _normalize_headers(self):
        self.df.columns = [
            (a, "" if isinstance(b, str) and b.startswith("Unnamed") else b)
            for a, b in self.df.columns
        ]

    def _remove_non_class_columns(self):
        target_class = "KS2 BF2"
        columns = self.df.columns.tolist()

        # remove columns
        class_cols = []
        for col in columns:
            if col[1] in self.fach_std_translate.keys():
                class_cols.append(col)
                if col[0] == target_class and col[1] == "Std":
                    break  # Stop once KS2 BF2 / Stunden is reached

        self.df = self.df[class_cols]

    def _standardize_columns(self):
        self.df.columns = pd.MultiIndex.from_tuples(
            [
                (
                    (col[0], self.fach_std_translate[col[1]])
                    if col[1] in self.fach_std_translate.keys()
                    else col
                )
                for col in self.df.columns
            ]
        )

    def _extract_class_columns(self):
        """Finds all valid class columns by scanning for ('Klasse', 'Fach') / 'Stunden' pairs."""
        class_names = []
        for col1, col2 in self.df.columns:
            if col2 == "Fach":
                class_names.append(col1)
        return class_names

    def _remove_non_teacher_rows(self):
        self.df = self.df[self.df.index.to_series().apply(is_valid_teacher)]

    def _extract_teacher_meta(self):
        # Extract specific columns from original DataFrame
        cols = [("Deputat 24/25", ""), ("Anr", "Std"), ("Bonus", "")]
        print("cols:\n", self.df.columns)
        available = [col for col in self.df.columns if col in cols]
        if not available:
            return pd.DataFrame()
        print("teacher meta:\n", self.df[available].rename(columns=lambda x: x[0]))

        return (
            self.df[available].rename(columns=lambda x: x[0]).fillna(0)
        )  # Flatten to single-level

    def get_df(self, reset_index=False):
        if reset_index:
            df_copy = self.df.copy()
            return df_copy.reset_index()
        return self.df

    def get_teaching_load(self, teacher):
        """
        Return a dict with {'Deputat 24/25': ..., 'Anr': ..., 'Bonus': ...}
        """
        if teacher not in self.teaching_loads.index:
            return {}

        return self.teaching_loads.loc[teacher].to_dict()

    def get_total_lessons(self, teacher):
        """
        Sum all non-null Stunden entries for this teacher
        """
        if teacher not in self.df.index:
            return 0

        stunden_cols = [col for col in self.df.columns if col[1] == "Std"]
        return (
            pd.to_numeric(self.df.loc[teacher, stunden_cols], errors="coerce")
            .fillna(0)
            .sum()
        )

    def compare_load(self, teacher):
        """
        Return a summary of assigned vs expected load
        """
        load = self.get_teaching_load(teacher)
        actual = self.get_total_lessons(teacher)
        expected = (
            load.get("Deputat 24/25", 0) - load.get("Anr", 0) - load.get("Bonus", 0)
        )

        return {
            "teacher": teacher,
            "assigned": actual,
            "expected": expected,
            "delta": actual - expected,
        }

    def get_classes(self):
        """Return list of all class names that have 'Fach' and 'Std' columns."""
        return sorted({col[0] for col in self.df.columns if col[1] == "Std"})

    def get_teachers_in_class(self, class_name):
        """Return teachers who teach in a given class."""
        if (class_name, "Std") not in self.df.columns:
            return []

        mask = self.df[(class_name, "Std")].fillna(0).astype(float) > 0
        subset = self.df.loc[
            mask, [(class_name, "Fach"), (class_name, "Std")]
        ].reset_index()
        subset.columns = ["Lehrer", "Fach", "Std"]
        return subset.to_dict(orient="records")

    def get_classes_of_teacher(self, teacher_name):
        """Return all classes where a given teacher teaches with subject and hours."""
        if teacher_name not in self.df.index:
            return []

        result = []
        for col in self.get_classes():
            try:
                subject = self.df.loc[teacher_name, (col, "Fach")]
                hours = self.df.loc[teacher_name, (col, "Std")]
                if pd.notna(hours) and float(hours) > 0:
                    result.append({"Class": col, "Subject": subject, "Lessons": hours})
            except KeyError:
                continue
        return result

    def build_wide_class_table(self):
        class_blocks = []
        max_rows = 0

        for class_name in self.class_columns:
            fach_col = (class_name, "Fach")
            stunden_col = (class_name, "Std")

            # Skip if either column missing
            if fach_col not in self.df.columns or stunden_col not in self.df.columns:
                continue

            # Filter only teachers with lessons in that class
            sub_df = self.df[self.df[stunden_col].notna()][
                [fach_col, stunden_col]
            ].copy()
            sub_df = sub_df.rename(
                columns={
                    fach_col: f"{class_name} – Fach",
                    stunden_col: f"{class_name} – Std",
                }
            )
            sub_df.insert(0, f"{class_name} – Teacher", sub_df.index)

            sub_df = sub_df.reset_index(drop=True)
            max_rows = max(max_rows, len(sub_df))
            class_blocks.append(sub_df)

        # Pad all blocks to the same number of rows
        for i in range(len(class_blocks)):
            block = class_blocks[i]
            if len(block) < max_rows:
                # Add empty rows
                pad_size = max_rows - len(block)
                padding = pd.DataFrame(
                    [[""] * block.shape[1]] * pad_size, columns=block.columns
                )
                class_blocks[i] = pd.concat([block, padding], ignore_index=True)

        # Concatenate all blocks side-by-side
        wide_df = pd.concat(class_blocks, axis=1)
        return wide_df

    def get_dashboard_rows(self):
        teacher_names = self.df.index.tolist()
        rows = []

        for name in teacher_names:
            load = self.compare_load(name)
            meta = self.get_teaching_load(name)
            load["dep"] = meta.get("Deputat 24/25", 0)
            load["anr"] = meta.get("Anr", 0)
            load["bonus"] = meta.get("Bonus", 0)
            load["teacher"] = name
            rows.append(load)

        return rows
