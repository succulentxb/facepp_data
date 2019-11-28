import os
import time
import requests
import xlsxwriter  # 使用该依赖包，可避免单个单个单元格最大字符数限制

IMGS_FOLDER_NAME = "imgs"
FACEPP_URL = "https://api-cn.faceplusplus.com/facepp/v1/face/thousandlandmark"
API_KEY = "{填写api_key}"
API_SECRET = "{填写api_secret}"
TIME_LATENCY = 2  # 每次请求间延迟，防止qps超限导致失败


class ImgPath:
    def __init__(self, path, name):
        self.path = path
        self.name = name

    def get_path(self):
        return os.path.join(self.path, self.name)


def get_img_list():
    imgs_path = os.path.join(os.curdir, IMGS_FOLDER_NAME)
    imgs_list = []
    for p, _, files in os.walk(imgs_path):
        for f in files:
            if f.endswith(".jpg") or f.endswith(".jpeg") or f.endswith("png"):
                imgs_list.append(ImgPath(p, f))
    return imgs_list


def facepp_post(img_file):
    if not img_file:
        return None
    files = {"image_file": img_file}
    params = {
        "api_key": API_KEY,
        "api_secret": API_SECRET,
        "return_landmark": "all"
    }
    response = requests.post(FACEPP_URL, data=params, files=files)
    if response.status_code != 200:
        print("[ERROR] [facepp_post] failed request data for img=%s, response=%s" % (img_file.name, response.json()))
        return None
    r_data = response.json()
    if not r_data.get("face"):
        print("[ERROR] [facepp_post] failed request data for img=%s, response=%s" % (img_file.name, r_data))
        return None
    return r_data.get("face")


def process_imgs():
    img_list = get_img_list()
    header = ["img_name", "img_path", "left_eyebrow", "right_eyebrow",
              "left_eye", "left_eye_eyelid", "right_eye", "right_eye_eyelid",
              "nose", "mouth", "face", "origin_data"]
    # result_f = open("data.csv", "w")
    # csv_writer = csv.writer(result_f)
    # csv_writer.writerow(header)
    workbook = xlsxwriter.Workbook("data.xlsx")
    sheet = workbook.add_worksheet("default")
    for i in range(len(header)):
        sheet.write(0, i, header[i])
    failed_list = img_list
    rown = 1
    while len(failed_list) > 0:
        img_list = failed_list
        failed_list = []

        for img in img_list:
            if not img:
                continue
            print("[INFO] [process_imgs] processing img=%s" % img.get_path())
            try:
                time.sleep(TIME_LATENCY)
                img_file = open(os.path.join(os.curdir, img.get_path()), "rb")
                resp = facepp_post(img_file)
                if not resp:
                    print("[ERROR] [process_imgs] failed process img=%s" % img.get_path())
                    failed_list.append(img)
                    continue
                data = resp.get("landmark", {})
                record = [
                    img.name,
                    img.get_path(),
                    str(data.get("left_eyebrow")),
                    str(data.get("right_eyebrow")),
                    str(data.get("left_eye")),
                    str(data.get("left_eye_eyelid")),
                    str(data.get("right_eye")),
                    str(data.get("right_eye_eyelid")),
                    str(data.get("nose")),
                    str(data.get("mouth")),
                    str(data.get("face")),
                    str(resp)
                ]
                for i in range(len(record)):
                    sheet.write(rown, i, record[i])
                rown += 1
                # csv_writer.writerow(record)
            except Exception as e:
                print("[ERROR] [process_imgs] error while process img=%s, err=%s" % (img.get_path(), e))
                failed_list.append(img)
        print("[INFO] failed list = %s" % failed_list)
    workbook.close()
    print("[INFO] [process_imgs] done!")


if __name__ == "__main__":
    process_imgs()
