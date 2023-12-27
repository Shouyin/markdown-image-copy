import re
import os
import urllib.parse
import shutil
import argparse
import base64

import requests

def image_to_base64(image_path):
    encoded_string = ""
    with open(image_path, 'rb') as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string

# ![Alt text](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA...)

ERROR_IMG = ""

global_name_i = 0

def mkdir(dir_path): 
    if not os.path.isdir(dir_path): os.mkdir(dir_path)

def new_rand_img_name(): return f"img{global_name_i}"

def get_filename_from_url(url):
    parsed_url = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed_url.path)
    filename = path.split('/')[-1]
    if "." not in filename:
        filename = new_rand_img_name()
    return filename


def download_img(url, pic_dir, line_num=-1):
    img_path = os.path.join(pic_dir, get_filename_from_url(url))
    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True)
        # Raise an exception if the request was unsuccessful
        response.raise_for_status()

        # Open the file in binary write mode
        with open(img_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        print(f"INFO: line {line_num}, File downloaded successfully: {img_path}")

    except requests.exceptions.HTTPError as e:
        print(f"WARNING: HTTP Error: {e}")
        return ERROR_IMG
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Error downloading file: {e}")
        return ERROR_IMG
    
    return img_path


def cp_img(path, pic_dir, mv, line_num=-1):
    new_path = os.path.join(pic_dir, os.path.basename(path))
    if mv:
        shutil.move(path, new_path)
    else:
        shutil.copy(path, new_path)
    return new_path
    

def get_img(path, pic_dir, mv=False, line_num=-1):
    # Check if the string is a valid URL
    if path[:2] == "//":
        path = "https:" + path
    parsed_url = urllib.parse.urlparse(path)
    if parsed_url.scheme and parsed_url.netloc:
        return download_img(path, pic_dir, line_num=line_num)

    # Check if the string is a local directory
    if os.path.isfile(path):
        return cp_img(path, pic_dir, mv, line_num=line_num)

    print(f"WARNING: line {line_num}, {path} does not exist.")
    return ERROR_IMG


########################################################################
# image: img tag
########################################################################
RE_IMG_TAG = re.compile(r"""<img(\s+[^>]*)src=["']([^"'>]+)["']([^>]*)>""")
def replace_imgtag(
    match, pic_dir, pic_dir_in_md, mv=False, line_num=-1, orig_img_base_dire="",
    b64mode=False
):
    orig_img_path = match.group(2)
    if orig_img_base_dire != "" and (not os.path.isabs(orig_img_path)):
        orig_img_path = os.path.join(orig_img_base_dire, orig_img_path)
    replaced_img_path = get_img(orig_img_path, pic_dir, mv=mv, line_num=line_num)
    if b64mode:
        b64img = image_to_base64(replaced_img_path)
        _, file_extension = os.path.splitext(replaced_img_path)
        replaced_img_path=f"data:image/{file_extension[1:]};base64,{str(b64img, encoding=('utf-8'))}"
    else:
        replaced_img_path = os.path.join(pic_dir_in_md, os.path.basename(replaced_img_path))
    modified_line = \
        f"""<img{match.group(1)}src="{replaced_img_path}"{match.group(3)}>"""
        # modified_line = f"""<img{match.group(1)}src="data:image/{file_extension[1:]};base64,{str(b64img)[2:-1]})"{match.group(3)}>"""
    return modified_line


RE_IMG_MDSYNTX = re.compile(r"!\[(.*)\]\((.*)\)")
def replace_img_mdsyntax(
    match, pic_dir, pic_dir_in_md, mv=False, line_num=-1, orig_img_base_dire="",
    b64mode=False
):
    orig_img_path = match.group(2)
    if orig_img_base_dire != "" and (not os.path.isabs(orig_img_path)):
        orig_img_path = os.path.join(orig_img_base_dire, orig_img_path)
    replaced_img_path = get_img(orig_img_path, pic_dir, mv=mv, line_num=line_num)
    if b64mode:
        b64img = image_to_base64(replaced_img_path)
        _, file_extension = os.path.splitext(replaced_img_path)
        replaced_img_path=f"data:image/{file_extension[1:]};base64,{str(b64img, encoding=('utf-8'))}"
    else:
        replaced_img_path = os.path.join(pic_dir_in_md, os.path.basename(replaced_img_path))
    
    modified_line = ""
    if b64mode:
        modified_line = f"""<img alt="{match.group(1)}" src="{replaced_img_path}" />"""
    else:
        modified_line = \
            f"""![{match.group(1)}]({replaced_img_path})"""
            # modified_line = f"""<img{match.group(1)}src="data:image/{file_extension[1:]};base64,{str(b64img)[2:-1]})"{match.group(3)}>"""
    return modified_line


def process_line(
    line, regex, process_func, pic_dir, pic_dir_in_md, mv=False, line_num=-1,
    orig_img_base_dire="", b64mode=False
):
    start_index = 0
    processed_line = ""
    for match in regex.finditer(line):
        if processed_line and b64mode:
            processed_line += "\n"
        # matched a image in md
        match_start, match_end = match.span()
        processed_line += line[start_index:match_start]

        # replace the image path
        modified_match = process_func(match, pic_dir, pic_dir_in_md,
                                      mv=mv, line_num=line_num,
                                      orig_img_base_dire=orig_img_base_dire,
                                      b64mode=b64mode)
        processed_line += modified_match
        start_index = match_end
    processed_line += line[start_index:]
    return processed_line


def default_pic_dire(md_path):
    pic_folder_name = os.path.basename(md_path).split(".")[0] + "_pics"
    return pic_folder_name

def default_processed_path(md_path):
    dire = os.path.dirname(md_path)
    filename = os.path.basename(md_path).split(".")[0] + "_processed" + ".md"
    return os.path.join(dire, filename)

def main(pic_dir, mv=False):
    parser = argparse.ArgumentParser(description="Markdown-image-copy: gather all image files in the markdown doc.")
    parser.add_argument("path", help="The path of markdown file")
    parser.add_argument("-m", "--move", help="Move local images instead of copying.", action="store_true")
    parser.add_argument("-d", "--dst", help="Destination directory to gather images to.", default="")
    parser.add_argument("-b", "--base64", help="Convert all images to base64, so that no need to save them to a dedicated directory", action="store_true")
    parser.add_argument("-x", "--nobackup", help="Modify the original markdown file, no backup is created.", action="store_true")
    args = parser.parse_args()
    path = args.path
    if not os.path.exists(path):
        print(f"ERROR: {path} does not exist.")
        exit(1)
    pic_dir = args.dst if args.dst else default_pic_dire(path)
    pic_dir_in_md = pic_dir
    if not os.path.isabs(pic_dir):
        pic_dir_in_md = os.path.join(".", pic_dir)
        pic_dir = os.path.join(os.path.dirname(path), pic_dir)
    
    processed_path = default_processed_path(path)

    mkdir(pic_dir)
    processed = []
    line_num = 0
    with open(path) as md_fd:
        for line in md_fd:
            
            line = process_line(
                line, RE_IMG_TAG, replace_imgtag, 
                pic_dir, pic_dir_in_md, mv=args.move, line_num=line_num,
                orig_img_base_dire=os.path.dirname(path),
                b64mode=args.base64
            )

            line = process_line(
                line, RE_IMG_MDSYNTX, replace_img_mdsyntax, 
                pic_dir, pic_dir_in_md, mv=args.move, line_num=line_num,
                orig_img_base_dire=os.path.dirname(path),
                b64mode=args.base64
            )
            
            processed.append(line)
            line_num += 1

    with open(processed_path, "w") as out_fd:
        out_fd.writelines(processed)

    if args.nobackup:
        # backup md
        shutil.move(processed_path, path)
        print(f"Saved to {path}")
    else:
        print(f"Saved to {processed_path}")

if __name__ == "__main__":
    PATH = "../Making games.md"
    PIC_DIR = "./pics"
    main(PATH, PIC_DIR)
