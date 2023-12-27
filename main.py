import re
import os
import urllib.parse
import shutil
import requests

SUCCESS_IMG = 0
ERROR_IMG = ""

global_name_i = 0

def mkdir(dir_path):
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

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

        print(f"File downloaded successfully: {img_path}")

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
    parsed_url = urllib.parse.urlparse(path)
    if parsed_url.scheme and parsed_url.netloc:
        return download_img(parsed_url, pic_dir, line_num=line_num)

    # Check if the string is a local directory
    if os.path.isfile(path):
        return cp_img(path, pic_dir, mv, line_num=line_num)

    print(f"WARNING: line {line_num}, {path} does not exist.")
    return ERROR_IMG


########################################################################
# image: img tag
########################################################################
RE_IMG_TAG = re.compile(r"""<img(\s+[^>]*)src=["']([^"'>]+)["']([^>]*)>""")
def replace_imgtag(match, pic_dir, mv=False, line_num=-1, orig_img_base_dire=""):
    orig_img_path = match.group(2)
    if orig_img_base_dire != "" and (not os.path.isabs(orig_img_path)):
        orig_img_path = os.path.join(orig_img_base_dire, orig_img_path)
    replaced_img_path = get_img(orig_img_path, pic_dir, mv=mv, line_num=line_num)
    modified_line = \
        f"""<img{match.group(1)}src="{replaced_img_path}"{match.group(3)}>"""
    return modified_line


def process_line(
    line, regex, process_func, pic_dir, mv=False, line_num=-1,
    orig_img_base_dire=""
):
    start_index = 0
    processed_line = ""
    for match in regex.finditer(line):
        # The start and end indices of the match
        match_start, match_end = match.span()

        # Add the part of the line before the match
        processed_line += line[start_index:match_start]

        # Replace some text within the match
        modified_match = process_func(match, pic_dir, 
                                      mv=mv, line_num=line_num,
                                      orig_img_base_dire=orig_img_base_dire)
        processed_line += modified_match

        # Update the start index
        start_index = match_end

    # Add the remainder of the line
    processed_line += line[start_index:]
    return processed_line


def main(path, pic_dir, mv=False):
    mkdir(pic_dir)
    processed = []
    line_num = 0
    with open(path) as md_fd:
        for line in md_fd:
            
            line = process_line(
                line,
                RE_IMG_TAG, replace_imgtag, 
                pic_dir, mv=mv, line_num=line_num,
                orig_img_base_dire=os.path.dirname(path)
            )
            
            processed.append(line)
            line_num += 1

    with open("./processed.md", "w") as out_fd:
        out_fd.writelines(processed)

if __name__ == "__main__":
    # TODO args
    # -m: move mode, default: copy mode
    # -d: dst directory
    # -b: base64 mode
    # -x: no backup, defualt: move the original doc to a backup

    PATH = "/Users/shouyin/Desktop/Projects/Making games.md"
    PIC_DIR = "./pics"
    main(PATH, PIC_DIR)
