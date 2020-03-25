import json
import logging

import xlsxwriter

URL_PREFIX = "https://smeal.ca1.qualtrics.com/ControlPanel/Graphic.php?IM="


if __name__ == "__main__":
    try:
        # This json file is extracted from qualtrics graphics library page source code
        f = open("qual_img_data.json")
        data = json.loads(f.read())
        f.close()

        folder_data = data["Faces_20190630"]

        # target result xlsx file
        result_workbook = xlsxwriter.Workbook("qualtrics_faces_urls.xlsx")
        sheet = result_workbook.add_worksheet()

        sheet.write(0, 0, "url")
        sheet.write(0, 1, "img")
        row = 1
        for key, val in folder_data:
            sheet.write(row, 0, URL_PREFIX+key)
            sheet.write(row, 1, val["Description"])
            row = row + 1
        result_workbook.close()
    except Exception as e:
        logging.warning("failed process, err=%s" % e)
