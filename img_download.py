import os

import xlrd
import requests

IMG_FOLDER = "insect"
EXCEL_NAME = "insect.xlsx"


def download_img(url, img_name):
    r = requests.get(url)
    if not r or r.status_code != 200:
        print("[ERROR] [download_img] failed request img, url=%s" % url)
        return False
    f = open(os.path.join(IMG_FOLDER, img_name), "w+b")
    f.write(r.content)
    f.close()
    return True


def read_img_info(filename=EXCEL_NAME):
    workbook = xlrd.open_workbook(filename)
    sheet = workbook.sheet_by_index(0)
    imgs = []
    for row in sheet.get_rows():
        imgs.append({
            "name": row[2].value + ".jpg",
            "url": row[1].value
        })
    return imgs[1:]


if __name__ == "__main__":
    img_list = read_img_info()
    for img in img_list:
        print("[INFO] start downloading img, url=%s, name=%s" % (img["url"], img["name"]))
        download_img(img["url"], img["name"])
    print("[INFO] download done.")
