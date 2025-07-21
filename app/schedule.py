import pandas as pd
import numpy as np
import json
from natsort import index_natsorted
from collections import defaultdict


from utils import is_valid_teacher, rename_columns


class TeacherSchedule:
    def __init__(self, excel_path, data_start_row=5):
        # class teacher and deputy data
        self.df = pd.read_excel(excel_path, header=[0, 1])
        self.df = self.df.iloc[data_start_row:].copy()
        # self.main_teachers_row = pd.read_excel(excel_path, header=None).iloc[2]
        # self.deputy_teachers_row = pd.read_excel(excel_path, header=None).iloc[3]
        self.raw_df = pd.read_excel(excel_path, header=None)

        # print("main teachers row:\n", self.main_teachers_row)
        # self.main_teachers_row = raw_df.iloc[2] 
        # self.deputy_teachers_row = raw_df.iloc[3] 
        # self.df = raw_df.iloc[data_start_row:].copy()
        # self.df = pd.read_excel(excel_path, header=[0, 1], skiprows=data_start_row - 1)
        # self.df = pd.read_excel(excel_path, header=[0, 1], skiprows=data_start_row - 1)
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
        self.class_teachers = self._extract_class_teachers()
        self._remove_non_class_columns()
        self._standardize_columns()
        self.class_columns = self._extract_class_columns()
        #self.grade_columns = set([col[0] for col in self.class_columns])
        self.grade_columns = ["5", "6", "7", "8", "9", "10", "KS1", "KS2"]
        print("class columns:\n", self.class_columns)

    def _get_excel_col_index(self, col_tuple):
        """Find the original Excel column index for a given MultiIndex column."""
        # Look in the first two rows of raw_df for matching headers
        for i, (lvl0, lvl1) in enumerate(zip(self.raw_df.iloc[0], self.raw_df.iloc[1])):
            if str(lvl0).strip() == col_tuple[0] and str(lvl1).strip() == col_tuple[1]:
                return i
        raise ValueError(f"Column {col_tuple} not found in raw_df headers.")

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
        self.df = self.df.loc[:, ~self.df.columns.get_level_values(1).str.contains(r"^Std\.\d+$")]

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
        cols = [
            ("Deputat 24/25", ""),
            ("Anr", "Std"),
            ("Bonus", ""),
            ("Sonderaufgaben", "Bg"),
            ("Ags [unter Vorbehalt]", "AG"),
            ("Ags [unter Vorbehalt]", "Std"),
            ("Poolstd [unter Vorbehalt]", "Bg"),
            ("Poolstd [unter Vorbehalt]", "Std"),
        ]
        # print("cols:\n", self.df.columns)
        available = [col for col in self.df.columns if col in cols]
        if not available:
            return pd.DataFrame()
        
        result_df = self.df[available].rename(columns=lambda x: rename_columns(x))
        
        # handle missing values
        result_df[result_df.select_dtypes(include="number").columns] = result_df.select_dtypes(include="number").fillna(0)
        result_df[result_df.select_dtypes(include="object").columns] = result_df.select_dtypes(include="object").fillna("")

        return result_df

    
    def _extract_class_teachers(self):
        class_teachers = {}
        # Columns from the actual data table (e.g., ('5a', 'Fach'), ...)
        class_cols = [col for col in self.df.columns if col[1] == 'Fach']
        
        for col in class_cols:
            col_idx = self._get_excel_col_index(col)  # We'll define this next

            # Fetch main and deputy teachers from row 3 and 4 (raw_df)
            main_teacher = self.raw_df.iloc[2, col_idx]
            deputy_teachers = self.raw_df.iloc[3, col_idx]

            class_name = col[0]
            deputies = [
                d.strip() for d in str(deputy_teachers).split(",") if d.strip()
            ] if pd.notna(deputy_teachers) else []

            class_teachers[class_name] = {
                "main": str(main_teacher).strip() if pd.notna(main_teacher) else None,
                "deputies": deputies
            }

        return class_teachers

    
    def get_df(self, reset_index=False):
        if reset_index:
            df_copy = self.df.copy()
            return df_copy.reset_index()
        return self.df

    def get_teaching_load(self, teacher):
        """
        Return a dict with {'Deputat 24/25': ..., 'Anr': ..., 'Bonus': ..., 'Sonderuafgaben': ...}
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
            load.get("Deputat 24/25", 0) 
            - load.get("Anr", 0) 
            - load.get("Bonus", 0)
            - load.get("Ags-Std", 0) 
            - load.get("Poolstd-Std", 0)
        )

        return {
            "teacher": teacher,
            "assigned": actual, # WS
            "expected": expected, # Deputat Netto
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

    def build_wide_class_table(self, sort):
        
        wide_df_list = []

        for grade in self.grade_columns:
            wide_df = dict()
            class_blocks = []
            max_rows = 0
            for class_name in list(filter(lambda x: x.startswith(grade), self.class_columns)):  # self.class_columns:
                fach_col = (class_name, "Fach")
                stunden_col = (class_name, "Std")
                main_teachers_for_class = self.class_teachers.get(class_name, {})
                print(f"main_teachers_for_class: {main_teachers_for_class}")


                # Skip if either column missing
                if fach_col not in self.df.columns or stunden_col not in self.df.columns:
                    continue

                # Filter only teachers with lessons in that class
                sub_df = self.df[self.df[stunden_col].notna()][
                    [fach_col, stunden_col]
                ].copy()
                # sub_df = sub_df.rename(
                #     columns={
                #         fach_col: f"{class_name} – Fach",
                #         stunden_col: f"{class_name} – Std",
                #     }
                # )
                sub_df.columns = [f"{col[0]} – {col[1]}" for col in sub_df.columns]
                sub_df.insert(0, f"{class_name} – Teacher", sub_df.index)

                f = lambda col: np.argsort(index_natsorted(col.str.lower().str.normalize('NFD')))

                if sort == "teacher":
                    sub_df = sub_df.sort_values(by=f"{class_name} – Teacher", key=f).reset_index(drop=True)

                elif sort == "fach":
                    sub_df = sub_df.sort_values(by=f"{class_name} – Fach", key=f).reset_index(drop=True)

                sub_df = sub_df.reset_index(drop=True)


                # add main teachers
                if main_teachers_for_class:     
                    empty_row = ["", "", ""]               
                    main_teacher_row = ["KL:", main_teachers_for_class.get("main"), ""]
                    deputies = main_teachers_for_class.get("deputies")
                    deputies_string = ", ".join(deputies)
                    deputies_row = ["TP:", deputies_string, ""]
                    new_rows = [empty_row, main_teacher_row, deputies_row]
                    new_df = pd.DataFrame(new_rows, columns=sub_df.columns)
                    sub_df = pd.concat([sub_df, new_df], ignore_index=True)

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
            wide_df['df'] = pd.concat(class_blocks, axis=1)
            wide_df['grade'] = grade
            wide_df_list.append(wide_df)
        return wide_df_list

    def get_dashboard_rows(self):
        teacher_names = self.df.index.tolist()
        rows = []

        for name in teacher_names:
            load = self.compare_load(name)
            meta = self.get_teaching_load(name)
            load["dep"] = meta.get("Deputat 24/25", 0)
            load["anr"] = meta.get("Anr", 0)
            load["bonus"] = meta.get("Bonus", 0)
            load['ags'] = meta.get("Ags-Std", 0)
            load['pool'] = meta.get("Poolstd-Std", 0)
            load["teacher"] = name
            rows.append(load)

        return rows
    
    def get_teacher_schedule_long(self):
        rows = []
        df = self.df.copy()

        # Index contains teacher names
        teacher_names = df.index


        # Get all class names by scanning second-level column headers
        class_names = sorted(set([col[0] for col in df.columns if col[1] == "Fach"]))

        for teacher in teacher_names:
            row = df.loc[teacher]

            for cls in class_names:
                fach_col = (cls, "Fach")
                std_col = (cls, "Std")

                if fach_col not in df.columns or std_col not in df.columns:
                    continue

                fach = row.get(fach_col)
                stunden = row.get(std_col)

                if pd.notna(stunden):
                    rows.append({
                        "Lehrer": teacher,
                        "Klasse": cls,
                        "Fach": fach,
                        "Stunden": stunden,
                    })

        return pd.DataFrame(rows)
    

    


