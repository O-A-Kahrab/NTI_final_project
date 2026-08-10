import os

def Exact_Search(file_name,file_type,directory):
    """searches for a file with the exact name
       takes 3 arguments name of file, its type 
       and possible directories that may contain 
       the file. returns the directory of the file 
       if found otherwise return None"""
    if file_type != None: #to make sure it is not a folder
        file_name = file_name+file_type 
    #to examine name and type at the same time

    for root,dirs,files in os.walk(directory):
        #walk returns the (the directory inserted, a list of all sub-directories, a list of all names for the files in the directory)
        #The loop will help examine each and every sub-directories and all there sub-directories
        
        if file_name in files:
            return os.path.join(root,file_name)
    return None

def advanced_file_search(file_name,file_type,directory):
    pass

