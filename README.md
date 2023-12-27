# markdown-image-copy

Copy/download all images in a markdown file to one place, or convert them to base64 (making the markdown doc self-contained).

## Usage
```
# save images to directory pics that locates in the same directory of where markdown_doc.md locates
python3 main.py "markdown_doc.md" -d "pics"

# convert image paths to base64 images
python3 main.py "markdown_doc.md" -b

# move images, instead of copying
python3 main.py "markdown_doc.md" -m
```