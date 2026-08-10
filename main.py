from functions import *

file_name = input("Enter the exact name of the file: ") #target file

# print("1-folder    2-.exe    3-.pptx\n4-.txt    5-.dll    6-jpg")#the print and the list will be continued by ai
# n = input("Enter a number for one of the previous file types: ")
# #n will be an index 
# types = ["folder",".exe",]
#file_type = types[n - 1] #instead of if statments

file_type = input("type: ")
directories = input("Enter directories to search in (seperate them using slashes -\\-): ") #list of directories
for directory in directories.split(sep="/"):
    found_directory = Exact_Search(file_name,file_type,directory)
print("The file was found at:\n\t",found_directory)

