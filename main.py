from functions import *
import os
file_name = input("Enter the exact name of the file: ") #target file


extention = input("Enter the extention (enter -1 for folder): ")
#n will be an index 
file_extensions = [
    ".3gp",
    ".7z",
    ".aac",
    ".apk",
    ".avi",
    ".bat",
    ".bin",
    ".bmp",
    ".bz2",
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".dll",
    ".doc",
    ".docx",
    ".epub",
    ".exe",
    ".flac",
    ".flv",
    ".gif",
    ".gz",
    ".heic",
    ".htm",
    ".html",
    ".ico",
    ".java",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".log",
    ".m4a",
    ".m4v",
    ".md",
    ".mid",
    ".midi",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".msi",
    ".ods",
    ".odt",
    ".ogg",
    ".pdf",
    ".php",
    ".png",
    ".ppt",
    ".pptx",
    ".psd",
    ".py",
    ".rar",
    ".rb",
    ".rtf",
    ".sh",
    ".sql",
    ".svg",
    ".sys",
    ".tar",
    ".tif",
    ".tiff",
    ".ts",
    ".tsv",
    ".txt",
    ".wav",
    ".webp",
    ".wma",
    ".wmv",
    ".xls",
    ".xlsx",
    ".xml",
    ".yaml",
    ".yml",
    ".zip",
]
#file_type = file_extensions[n - 1] #instead of if statments
while True:
    count = 0
    directories = input("Enter directories to search in (seperate them using slashes -/-): ") #list of directories

    for dir in directories.split("/"):
        if os.path.isdir(dir):
            count += 1

    if count == len(directories.split("/")):
        break
    else:
        print("Invalid directory")

for directory in directories.split(sep="/"):
    found_directory = Exact_Search(file_name,extention,directory)
    
if found_directory == None:
    print("File not found")
else:
    print("The file was found at:\n\t",found_directory)

#we can add search history as .json file ot just .txt file
#for json the searched name is the key and its content is a list of returned directories