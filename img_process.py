import os
import io

import xlrd
import requests
from PIL import Image, ImageDraw

# 本文件依赖于face_data.py产生的数据

# 图片路径类型，若读取本地文件则使用local, 若读取远程图片则是哟哦那个url
PATHTYPE = "url"  # url or local

# 若使用远程图片，则将远程图片信息存在下面的文件中, 数据格式应与face++_589.xlsx保持一致
PATHFILE = "face++_589.xlsx"
PATH2NAME = {}  # 全局变量请勿修改

# 前置数据，face_data.py产生的数据
DATA_PATH = "data_new.xlsx"


def read_img_data(filename, path_type="local"):
    workbook = xlrd.open_workbook(filename)
    sheet = workbook.sheet_by_index(0)
    
    heads = []
    # t = ""
    # t.endswith
    head_row = sheet.row(0)
    for head in head_row:
        heads.append(head.value)
    
    img_data_list = []
    for row_idx in range(1, sheet.nrows):
        row = sheet.row(row_idx)
        points = []
        for col_idx in range(3, sheet.ncols):
            if heads[col_idx].endswith("_x"):
                points.append((int(row[col_idx].value), int(row[col_idx+1].value)))
        img_data_list.append({
            "path": row[1].value,
            "path_type": path_type,
            "points": points
        })

    return img_data_list
    # print(img_data_list[0])


def draw_points(path, path_type, points):
    if not path:
        raise Exception("img path cannot be None or ''")

    img = None
    if path_type == "url":
        r = requests.get(path)
        if not r or r.status_code != 200:
            print("[ERROR] failed request img, path=%s" % path)
        f = io.BytesIO(r.content)
        img = Image.open(f)
    else:
        img = Image.open(path)
    d = ImageDraw.Draw(img)
    d.point(points)
    
    if path_type == "url":
        fn = PATH2NAME.get(path)
        img.save(os.path.join("./processed", "web", fn))
    else:
        img.save(os.path.join("./processed", img.filename))
    img.close()


def init_path2name():
    workbook = xlrd.open_workbook(PATHFILE)
    sheet = workbook.sheet_by_index(0)
    global PATH2NAME
    for row in sheet.get_rows():
        PATH2NAME[row[2].value] = row[1].value
    


if __name__ == "__main__":
    if PATHTYPE == "url":
        init_path2name()
    imgs = read_img_data("data_new.xlsx", PATHTYPE)
    print("[INFO] img info read done.")
    for img in imgs:
        print("[INFO] processing img, path=%s" % img.get("path"))
        draw_points(img.get("path"), PATHTYPE, img.get("points"))