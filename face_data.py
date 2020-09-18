import os
import time
import json
import logging

import requests
import xlrd
import xlsxwriter  # 使用该依赖包，可避免单个单个单元格最大字符数限制

# 修改此处，调整数据读取模式
# 支持两种MODE, 1读取本地图片文件进行分析, 2读取表格内数据进行请求分析
DATA_MODE = 1

# 如果需要读取本地文件，则将图片放在该目录下
IMGS_FOLDER_NAME = "many_origin"

# 如果使用读取表格内数据，则将下面变量修改为表格文件名，表格数据格式要求与face++_589.xlsx一致
IMGS_EXCEL_FILENAME = "face++_589.xlsx"

# Face++ API 接口地址，请勿修改
FACEPP_DENSE_URL = "https://api-cn.faceplusplus.com/facepp/v1/face/thousandlandmark"
FACEPP_FACIAL_FEATURE_URL = "https://api-cn.faceplusplus.com/facepp/v1/facialfeatures"

# 调用接口枚举
METHOD_DENSE = 1  # 人脸稠密点分析
METHOD_FACIAL_FEATURE = 2  # 面部特征识别

METHOD_URL_MAP = {
    METHOD_DENSE: FACEPP_DENSE_URL,
    METHOD_FACIAL_FEATURE: FACEPP_FACIAL_FEATURE_URL
}

# 修改此处，指定调用方法
# 指定调用方法，候选项为上面的接口枚举
METHOD = METHOD_DENSE

# Face++ API_KEY, API_SECRET, 此处为了安全隐去值，运行时需重新填上
API_KEY = "o3_cIVBPuV5UiDXgX0v9PM0eJMZB5djl"
API_SECRET = "YgzUh-B6ryMYOEzkj3XbOvWQuF9p72hL"

# 每次请求间延迟，防止qps超限导致失败，修改此处可以调整程序运行速度
# 但是延时过低会使请求失败率升高
TIME_LATENCY = 0.5

# 结果输出文件
RESULT_FILE = "feature_data_20200918.xlsx"

# 数据解析结构，请勿自行修改
# 人脸稠密点返回结果解析
DENSE_LANDMARK_SETTINGS = [
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

logging.basicConfig(level=logging.INFO)


class ImgPath:
    URL_PATH_TYPE = 1
    FILE_PATH_TYPE = 2

    def __init__(self, name, uri_type, uri, retry=20):
        self.uri_type = uri_type
        self.uri = uri
        self.name = name
        self.retry = retry

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


def facepp_post(method, img_file=None, params=None):
    if method not in METHOD_URL_MAP:
        logging.error("[facepp_post] invalid method")
        return None
    url = METHOD_URL_MAP[method]
    files = None
    if img_file:
        files = {"image_file": img_file}
    post_params = {
        "api_key": API_KEY,
        "api_secret": API_SECRET,
        "return_landmark": "all"
    }
    if params:
        post_params.update(params)
    # if img_url:
    #     post_params["image_url"] = img_url
    response = requests.post(url, data=post_params, files=files)
    if response.status_code != 200:
        logging.error("[facepp_post] failed request data, http status code=%s" % response.status_code)
        return None
    r_data = response.json()
    if r_data.get("error_message"):
        logging.error("[facepp_post] failed request data, error_message=%s" % r_data.get("error_message"))
        return None
    return r_data


def get_data_headers():
    headers = []
    for lm in DENSE_LANDMARK_SETTINGS:
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


def fetch_imgs_data(img_list, method, retry=10):
    failed_list = img_list
    result_list = []
    try:
        while len(failed_list) > 0 and retry > 0:
            img_list = failed_list
            failed_list = []

            for img in img_list:
                if not img:
                    continue
                logging.info("[process_imgs] processing img=%s" % img.uri)
                try:
                    time.sleep(TIME_LATENCY)
                    resp = None
                    params = {}
                    if method == METHOD_DENSE:
                        params = {"return_landmark": "all"}
                    elif method == METHOD_FACIAL_FEATURE:
                        pass

                    if img.uri_type == ImgPath.FILE_PATH_TYPE:
                        img_file = open(os.path.join(os.curdir, img.uri), "rb")
                        resp = facepp_post(method=method, img_file=img_file, params=params)
                        img_file.close()
                    elif img.uri_type == ImgPath.URL_PATH_TYPE:
                        params["image_url"] = img.uri
                        resp = facepp_post(method=method, params=params)

                    if not resp:
                        logging.error("[process_imgs] failed process img=%s" % img.uri)
                        failed_list.append(img)
                        continue

                    result_list.append({
                        "img": img,
                        "data": resp
                    })
                    logging.info("[process_imgs] success img=%s" % img.uri)
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    logging.error("[process_imgs] error while process img=%s, err=%s" % (img.uri, e))
                    failed_list.append(img)
            logging.info("failed list = %s" % failed_list)
            retry -= 1
    except KeyboardInterrupt as e:
        print("[process_imgs] user key interrupt, data saving, please not quit.")
        return result_list

    return result_list


def write_dense_data(result_list, start_row):
    header = ["img_name", "img_path", "origin_data"] + get_data_headers()
    # workbook = xlsxwriter.Workbook(RESULT_FILE)
    # sheet = None
    rown = start_row
    if rown > 0:
        workbook = copy_xlsx(RESULT_FILE)
        sheet = workbook.get_worksheet_by_name("default")
    else:
        workbook = xlsxwriter.Workbook(RESULT_FILE)
        sheet = workbook.add_worksheet("default")
        for i in range(len(header)):
            sheet.write(0, i, header[i])
        rown += 1
    for result in result_list:
        if not result:
            continue
        img = result.get("img")
        resp_data = result.get("data", {})
        origin_data = resp_data.get("face", {})
        data = origin_data.get("landmark")
        if not data:
            logging.error("[write_data] no data for img=%s" % img.name)
            continue
        row_data = [img.name, img.uri, json.dumps(origin_data)]
        for lm in DENSE_LANDMARK_SETTINGS:
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


FEATURE_DATA_HEADERS = ['angulus_oculi_medialis', 'eyes_type', 'eye_height', 'eye_width',
                        'mouth_height', 'mouth_width', 'lip_thickness', 'mouth_type', 'angulus_oris',
                        'golden_triangle', 'eyes_ratio', 'righteye_empty_result', 'righteye_empty_length',
                        'righteye_empty_ratio', 'lefteye_empty_result', 'lefteye_empty_length', 'lefteye_empty_ratio',
                        'lefteye', 'eyein_ratio', 'eyein_result', 'eyein_length', 'righteye', 'jaw_type', 'jaw_length',
                        'jaw_width', 'jaw_angle', 'faceup_ratio', 'faceup_result', 'faceup_length', 'facedown_length',
                        'facedown_result', 'facedown_ratio', 'facemid_length', 'facemid_ratio', 'facemid_result',
                        'parts_ratio', 'nose_width', 'nose_type', 'eyebrow_type', 'brow_height', 'brow_camber_angle',
                        'brow_uptrend_angle', 'brow_width', 'brow_thick', 'face_length', 'E', 'ABD_ratio',
                        'mandible_length', 'tempus_length', 'face_type', 'zygoma_length']


def write_feature_data(result_list, start_row):
    headers = ["img_name", "img_path", "origin_data"] + FEATURE_DATA_HEADERS
    # workbook = xlsxwriter.Workbook(RESULT_FILE)
    # sheet = workbook.add_worksheet("default")
    rown = start_row
    if rown > 0:
        workbook = copy_xlsx(RESULT_FILE)
        sheet = workbook.get_worksheet_by_name("default")
    else:
        workbook = xlsxwriter.Workbook(RESULT_FILE)
        sheet = workbook.add_worksheet("default")
        for i in range(len(headers)):
            sheet.write(0, i, headers[i])
        rown += 1
    for result in result_list:
        if not result:
            continue
        img = result.get("img")
        resp_data = result.get("data")
        origin_data = resp_data.get("result")
        row_data = [img.name, img.uri, json.dumps(origin_data)]
        leafs = parse_all_dict_leaf(origin_data)
        for header in FEATURE_DATA_HEADERS:
            row_data.append(leafs.get(header))

        for i in range(len(row_data)):
            sheet.write(rown, i, row_data[i])
        rown += 1
    workbook.close()


def parse_all_dict_leaf(dic):
    if type(dic) is dict:
        leaf_list = {}
        for k, v in dic.items():
            parse_res = parse_all_dict_leaf(v)
            if parse_res is None:
                leaf_list[k] = v
            else:
                leaf_list.update(parse_res)
        return leaf_list
    return None


def success_img_list(xlsx_file):
    start_row = 0
    try:
        workbook = xlrd.open_workbook(xlsx_file)
    except FileNotFoundError:
        return [], start_row
    if workbook is None:
        return [], start_row
    sheet = workbook.sheet_by_name("default")
    if sheet is None:
        return [], start_row
    rows = sheet.get_rows()
    start_row = sheet.nrows
    img_name_list = []
    for row in rows:
        img_name_list.append(row[0].value)
    return img_name_list[1:], start_row


def copy_xlsx(filename):
    wk_r = xlrd.open_workbook(filename)
    wk_w = xlsxwriter.Workbook(filename)
    sheet_r = wk_r.sheet_by_name("default")
    sheet_w = wk_w.add_worksheet("default")
    nrow = 0
    for row in sheet_r.get_rows():
        for ncol in range(len(row)):
            sheet_w.write(nrow, ncol, row[ncol].value)
        nrow += 1
    return wk_w


if __name__ == "__main__":
    imgs = None
    if DATA_MODE == 2:
        imgs = read_excel_img_list()
    elif DATA_MODE == 1:
        imgs = get_folder_img_list()
    success_list, start_r = success_img_list(RESULT_FILE)
    filtered_imgs = []
    for img in imgs:
        if img.name not in success_list:
            filtered_imgs.append(img)
    method = METHOD
    results = fetch_imgs_data(filtered_imgs, method)
    if method == METHOD_FACIAL_FEATURE:
        write_feature_data(results, start_r)
    elif method == METHOD_DENSE:
        write_dense_data(results, start_r)
    logging.info("[main] data done!")
