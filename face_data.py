import os
import time
import json

import requests
import xlrd
import xlsxwriter  # 使用该依赖包，可避免单个单个单元格最大字符数限制

# 支持两种MODE, 1读取本地图片文件进行分析, 2读取表格内数据进行请求分析
DATA_MODE = 1

# 如果需要读取本地文件，则将图片放在该目录下
IMGS_FOLDER_NAME = "imgs"

# 如果使用读取表格内数据，则将下面变量修改为表格文件名，表格数据格式要求与face++_589.xlsx一致
IMGS_EXCEL_FILENAME = "face++_589.xlsx"

# Face++ API 接口地址，请勿修改
FACEPP_URL = "https://api-cn.faceplusplus.com/facepp/v1/face/thousandlandmark"

# Face++ API_KEY, API_SECRET, 此处为了安全隐去值，运行时需重新填上
API_KEY = "oDfy0oKBV9tVCb4du72I3Bz7casKd9gD"
API_SECRET = "kQxG4MnqNeUAIiYxMEgBMMQl9ZWsi2eS"

# 每次请求间延迟，防止qps超限导致失败，修改此处可以调整程序运行速度
# 但是延时过低会使请求失败率升高
TIME_LATENCY = 1

# 结果输出文件
RESULT_FILE = "data_new.xlsx"

# 数据解析结构，请勿自行修改
LANDMARK_SETTINGS = [
    {
        "landmark": "face",
        "fields": [
            {"field": "face_hairline_", "range": (0, 145), "item": ["x", "y"]},  # range 前闭后开
            {"field": "face_contour_right_", "range": (0, 64), "item": ["x", "y"]},
            {"field": "face_contour_left_", "range": (0, 64), "item": ["x", "y"]}
        ]
    },
    {
        "landmark": "left_eyebrow",
        "fields": [
            {"field": "left_eyebrow_", "range": (0, 64), "item": ["x", "y"]}
        ]
    },
    {
        "landmark": "right_eyebrow",
        "fields": [
            {"field": "right_eyebrow_", "range": (0, 64), "item": ["x", "y"]}
        ]
    },
    {
        "landmark": "left_eye",
        "fields": [
            {"field": "left_eye_", "range": (0, 63), "item": ["x", "y"]},
            {"field": "left_eye_pupil_center", "range": None, "item": ["x", "y"]},
            {"field": "left_eye_pupil_radius", "range": None, "item": None}
        ]
    },
    {
        "landmark": "left_eye_eyelid",
        "fields": [
            {"field": "left_eye_eyelid_", "range": (0, 64), "item": ["x", "y"]}
        ]
    },
    {
        "landmark": "right_eye",
        "fields": [
            {"field": "right_eye_", "range": (0, 63), "item": ["x", "y"]},
            {"field": "right_eye_pupil_center", "range": None, "item": ["x", "y"]},
            {"field": "right_eye_pupil_radius", "range": None, "item": None}
        ]
    },
    {
        "landmark": "right_eye_eyelid",
        "fields": [
            {"field": "right_eye_eyelid_", "range": (0, 64), "item": ["x", "y"]}
        ]
    },
    {
        "landmark": "nose",
        "fields": [
            {"field": "nose_left_", "range": (0, 63), "item": ["x", "y"]},
            {"field": "nose_right_", "range": (0, 63), "item": ["x", "y"]},
            {"field": "right_nostril", "range": None, "item": ["x", "y"]},
            {"field": "left_nostril", "range": None, "item": ["x", "y"]},
            {"field": "nose_midline_", "range": (0, 60), "item": ["x", "y"]}
        ]
    },
    {
        "landmark": "mouth",
        "fields": [
            {"field": "upper_lip_", "range": (0, 64), "item": ["x", "y"]},
            {"field": "lower_lip_", "range": (0, 64), "item": ["x", "y"]}
        ]
    }
]


class ImgPath:
    URL_PATH_TYPE = 1
    FILE_PATH_TYPE = 2

    def __init__(self, name, uri_type, uri):
        self.uri_type = uri_type
        self.uri = uri
        self.name = name

    def __hash__(self):
        return hash(self.name+self.uri)

    def __str__(self):
        return self.name+" "+self.uri


def get_folder_img_list(folder=IMGS_FOLDER_NAME):
    imgs_path = os.path.join(os.curdir, folder)
    imgs_list = []
    for p, _, files in os.walk(imgs_path):
        for f in files:
            if f.endswith(".jpg") or f.endswith(".jpeg") or f.endswith("png"):
                imgs_list.append(ImgPath(f, ImgPath.FILE_PATH_TYPE, uri=os.path.join(p, f)))
    return imgs_list


def read_excel_img_list(filename=IMGS_EXCEL_FILENAME):
    workbook = xlrd.open_workbook(filename)
    sheet = workbook.sheet_by_index(0)
    imgs = []
    for row in sheet.get_rows():
        imgs.append(ImgPath(row[1].value, uri_type=ImgPath.URL_PATH_TYPE, uri=row[2].value))
    return imgs


def facepp_post(img_file=None, img_url=None):
    if not img_file and not img_url:
        print("[WARNING] [facepp_post] invalid param")
        return None
    files = {"image_file": img_file} if img_file else None
    params = {
        "api_key": API_KEY,
        "api_secret": API_SECRET,
        "return_landmark": "all",
    }
    if img_url:
        params["image_url"] = img_url
    response = requests.post(FACEPP_URL, data=params, files=files)
    if response.status_code != 200:
        print("[ERROR] [facepp_post] failed request data for img=%s, response=%s" %
              (img_file.name if img_file else img_url, response.json()))
        return None
    r_data = response.json()
    if not r_data.get("face"):
        print("[ERROR] [facepp_post] failed request data for img=%s, response=%s" %
              (img_file.name if img_file else img_url, r_data))
        return None
    return r_data.get("face")


def get_data_headers():
    headers = []
    for lm in LANDMARK_SETTINGS:
        fields = lm.get("fields")
        for field in fields:
            field_prefix = field.get("field")
            r = field.get("range")
            items = field.get("item")
            if r and items:
                for i in range(r[0], r[1]):
                    for item in items:
                        headers.append(field_prefix+str(i)+"_"+item)
            elif r and not items:
                for i in range(r[0], r[1]):
                    headers.append(field_prefix+str(i))
            elif not r and items:
                for item in items:
                    headers.append(field_prefix+"_"+item)
            elif not r and not items:
                headers.append(field_prefix)
    return headers


def fetch_imgs_data(img_list):
    failed_list = img_list
    result_list = []
    while len(failed_list) > 0:
        img_list = failed_list
        failed_list = []

        for img in img_list:
            if not img:
                continue
            print("[INFO] [process_imgs] processing img=%s" % img.uri)
            try:
                time.sleep(TIME_LATENCY)
                resp = None
                if img.uri_type == ImgPath.FILE_PATH_TYPE:
                    img_file = open(os.path.join(os.curdir, img.uri), "rb")
                    resp = facepp_post(img_file=img_file)
                elif img.uri_type == ImgPath.URL_PATH_TYPE:
                    resp = facepp_post(img_url=img.uri)
                if not resp:
                    print("[ERROR] [process_imgs] failed process img=%s" % img.uri)
                    failed_list.append(img)
                    continue

                result_list.append({
                    "img": img,
                    "data": resp
                })
            except Exception as e:
                print("[ERROR] [process_imgs] error while process img=%s, err=%s" % (img.uri, e))
                failed_list.append(img)
        print("[INFO] failed list = %s" % failed_list)
    return result_list


def write_data(result_list):
    header = ["img_name", "img_path", "origin_data"] + get_data_headers()
    workbook = xlsxwriter.Workbook(RESULT_FILE)
    sheet = workbook.add_worksheet("default")
    for i in range(len(header)):
        sheet.write(0, i, header[i])
    rown = 1
    for result in result_list:
        if not result:
            continue
        img = result.get("img")
        origin_data = result.get("data", {})
        data = origin_data.get("landmark")
        if not data:
            print("[ERROR] [write_data] no data for img=%s" % img.name)
            continue
        row_data = [img.name, img.uri, json.dumps(origin_data)]
        for lm in LANDMARK_SETTINGS:
            landmark = lm.get("landmark")
            lm_data = data.get(landmark)
            fields = lm.get("fields")
            for field in fields:
                prefix = field.get("field")
                r = field.get("range")
                items = field.get("item")
                if r:
                    for i in range(r[0], r[1]):
                        field_data = lm_data.get(prefix+str(i))
                        if items:
                            for item in items:
                                row_data.append(field_data.get(item))
                        else:
                            row_data.append(field_data)
                else:
                    field_data = lm_data.get(prefix)
                    if items:
                        for item in items:
                            row_data.append(field_data.get(item))
                    else:
                        row_data.append(field_data)
        for i in range(len(row_data)):
            sheet.write(rown, i, row_data[i])
        rown += 1
    workbook.close()


if __name__ == "__main__":
    imgs = None
    if DATA_MODE == 2:
        imgs = read_excel_img_list()
    if DATA_MODE == 1:
        imgs = get_folder_img_list()
    results = fetch_imgs_data(imgs)
    write_data(results)
    print("[INFO] [main] data done!")
