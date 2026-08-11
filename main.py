from functions import *
import os
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

invalid_name_char = ["\\","/",":",">","<","|",'"',"?","؟","*"]
while True:
    valid_flag = 1
    file_name = input("Enter the exact name of the file: ") #target file
    for char in file_name: #check for a valid file name
        if char in invalid_name_char:
            valid_flag = 0
            print("File names can't have any of these charcters",invalid_name_char)
    if valid_flag:
        break

while True: #make sure it is a valid extention
    extention = input("Enter the extention (enter -1 for folder): ")
    if extention == -1 or extention in file_extensions:
        break
    else:
        print("Invalid extention")

while True: #make sure it is a valid directory
    count = 0
    directories = input("Enter directories to search in (seperate them using slashes -/-): ") #list of directories

    for dir in directories.split("/"):
        if os.path.isdir(dir):
            count += 1

    if count == len(directories.split("/")):
        break
    else:
        print("Invalid directory")

found_directories = []
Exact_Search_flag = input("Enter one for exact search and zero for advanced serach")
if Exact_Search_flag == 1:
    for directory in directories.split(sep="/"):
        if directory == None:
            continue
        found_directories.append( Exact_file_Search(file_name,extention,directory) ) 
elif Exact_Search_flag == 0:
    for directory in directories.split(sep="/"):
            if directory == None:
                continue
            found_directories.append( advanced_file_search(file_name,extention,directory) ) 

if found_directories == []:
    print("File not found")
else:
    print("The file was found at:\n\t",found_directories)

#we can add search history as .json file ot just .txt file
#for json the searched name is the key and its content is a list of returned directories