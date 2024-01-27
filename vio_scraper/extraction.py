import numpy as np
import pandas as pd
from collections import Counter
from shapely.geometry import Polygon
from paddleocr import PaddleOCR

class TableExtraction:

    def __init__(self, *args, **kwargs):
        self.paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            show_log=False,
            leng="en",
            **kwargs
        )

    def text_box_from_ocr(self, image_path) -> list[tuple[tuple[float, float, float, float], str]]:
        """Given an image path, returns a list of tuple of box(x, y, w, h) and text"""

        def standardize_box(coords):
            a, _, c, _ = np.array(coords)
            x, y = a
            w, h = c - a

            return x, y, w, h

        result = self.paddle_ocr.ocr(image_path, cls=True)

        return [(standardize_box(box), text) for box, (text, _) in result[0]]


    def extract_table(self, data: dict[str, str | np.ndarray]) -> dict[str, list[list[str]]]:
        ocr = self.text_box_from_ocr(data["image"])
        return {
            "name" : data["name"],
            "data" : list(self.extract_table_from_ocr(ocr).itertuples(index=False, name=None))
        }
    
    def row_data_to_dataframe(self, rows, ocr_results, row_count, col_count):
        ocr_dict = dict(ocr_results)

        text_data = [[[] for _ in range(col_count)] for _ in range(row_count)]

        for idx, row in enumerate(rows):
            for cell_num, cell_box in row:
                text = ocr_dict[cell_box]
                text_data[idx][cell_num].append(text)  # noqa

        data = [[None for _ in range(col_count)] for _ in range(row_count)]

        for row_idx, row in enumerate(text_data):
            for col_idx, cell in enumerate(row):
                text = " ".join(text_data[row_idx][col_idx])
                data[row_idx][col_idx] = text or ""  # noqa

        df = pd.DataFrame(data)

        return df


    def extract_table_from_ocr(self, ocr_results: list[tuple[tuple[float, float, float, float], str]]) -> pd.DataFrame:
        boxes = [res[0] for res in ocr_results]

        row_count, col_count, rows = self.get_rows_from_boxes(boxes)

        dataframe = self.row_data_to_dataframe(rows, ocr_results, row_count, col_count)

        return dataframe
    
    def get_rows_from_boxes(self, ocr_boxes: list[tuple[float, float, float, float]]):
        """
        Given a list of box (x, y, w, h), returns a tuple of the following:
        - number of rows,
        - number of cols,
        - list of estimated where each value is an index and box
        """

        table = self.get_table_bounding_box(ocr_boxes)

        new_boxes = self.filter_boxes(ocr_boxes, table)

        non_overlap_box = self.get_non_overlapping_boxes(new_boxes)

        if row_vals := self.estimate_rows(non_overlap_box):
            reference_col, num_cols = self.estimate_reference_column(row_vals)
            cell_boundaries = self.cell_boundaries_along_x(reference_col)
            rows_with_cell_numbers = self.estimate_cell_numbers(row_vals, cell_boundaries)
            num_rows = len(rows_with_cell_numbers)

            return num_rows, num_cols, rows_with_cell_numbers

        return None
    
    def get_table_bounding_box(self, boxes):
        min_x = min(box[0] for box in boxes)
        min_y = min(box[1] for box in boxes)
        max_x = max(box[0] + box[2] for box in boxes)
        max_y = max(box[1] + box[3] for box in boxes)

        width = max_x - min_x
        height = max_y - min_y

        return min_x, min_y, width, height


    def filter_boxes(self, boxes, table, min_row: int = 3, min_col: int = 2):
        table_width = table[2] / min_col
        table_height = table[3] / min_row
        table_area = (table[2] * table[3]) / (min_row * min_col)

        filtered_boxes = [
            box for box in boxes if box[2] < table_width and box[3] < table_height and (box[2] * box[3]) < table_area
        ]

        return filtered_boxes
    
    def box_to_coords(self, box):
        x, y, w, h = box
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


    def get_non_overlapping_boxes(self, boxes):
        def box_overlap(box1, box2):
            polygon1 = Polygon(self.box_to_coords(box1))
            polygon2 = Polygon(self.box_to_coords(box2))
            return polygon1.contains(polygon2)

        # Sort the boxes by area
        sorted_boxes = sorted(boxes, key=lambda box: (box[1] * box[0]), reverse=True)

        non_overlapping_boxes = []

        while sorted_boxes:
            first_item = sorted_boxes.pop(0)

            is_inside_other_polygon = False

            for box in sorted_boxes:
                if box_overlap(box, first_item):
                    is_inside_other_polygon = True
                    break

            if not is_inside_other_polygon:
                non_overlapping_boxes.append(first_item)

        return non_overlapping_boxes


    def estimate_rows(self, boxes):
        non_overlapping_boxes = self.get_non_overlapping_boxes(boxes)

        # Sort the boxes based on y, then x
        sorted_boxes = sorted(non_overlapping_boxes, key=lambda box: (box[1], box[0]))

        rows = []

        while sorted_boxes:
            first_item = sorted_boxes.pop(0)

            col = [first_item]

            same_col_boxes = [box for box in sorted_boxes if first_item[1] <= box[1] <= (first_item[1] + first_item[3] / 2)]

            col.extend(same_col_boxes)

            for box in same_col_boxes:
                sorted_boxes.remove(box)

            col.sort(key=lambda box: box[0])

            rows.append(col)

        return rows


    def mode(self, arr):
        most_freq = Counter(arr).most_common()
        return most_freq[0][0]


    def estimate_reference_column(self, rows):
        if rows:
            row_lengths = [len(row) for row in rows]
            most_freq = self.mode(row_lengths)
            ele = [row for row in rows if len(row) == most_freq]
            return ele[0], most_freq

        return None


    def cell_boundaries_along_x(self, max_len_col):
        return [(x + 0.5, x + w - 0.5) for x, _, w, _ in max_len_col]


    def x_overlap_percentage(self, box, bound):
        x, y, w, h = box
        min_x, max_x = bound

        intersection = max(0, min(x + w, max_x) - max(x, min_x))
        overlap_percentage = (intersection / w) * 100

        return overlap_percentage


    def estimate_cell_numbers(self, rows, cell_bounds):
        result_rows: list[list] = []
        min_bound_x = cell_bounds[0][0]
        max_bound_x = cell_bounds[-1][1]

        for row in rows:
            temp_col = []

            for box in row:
                x, _, _, _ = box

                if x < min_bound_x:
                    cell_number = 0
                elif x >= max_bound_x:
                    cell_number = len(cell_bounds) - 1
                else:
                    _, cell_number = max(
                        ((self.x_overlap_percentage(box, bound), idx) for idx, bound in enumerate(cell_bounds)),
                        key=lambda x: x[0],
                    )

                temp_col.append((cell_number, box))

            result_rows.append(temp_col)

        return result_rows
