import shutil
import os
import logging

from face_data import RESULT_FILE, IMGS_FOLDER_NAME, success_img_list


SUCCESS_FOLDER = "success_imgs"


if __name__ == "__main__":
    try:
        os.mkdir(os.path.join(os.curdir, SUCCESS_FOLDER))
    except FileExistsError:
        logging.info("dst folder exist.")
    img_list, _ = success_img_list(RESULT_FILE)

    imgs_path = os.path.join(os.curdir, IMGS_FOLDER_NAME)
    dst_folder = os.path.join(os.curdir, SUCCESS_FOLDER)
    for p, _, files in os.walk(imgs_path):
        for f in files:
            if f in img_list:
                logging.info("[processing] successful img=%s found, moving..." % f)
                src_path = os.path.join(p, f)
                dst_path = os.path.join(dst_folder, f)
                shutil.move(src_path, dst_path)
