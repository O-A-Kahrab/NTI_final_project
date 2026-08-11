import os
from difflib import SequenceMatcher

def Exact_file_Search(file_name, file_type, directory):
    """searches for a file with the exact name
       takes 3 arguments name of file, its type 
       and possible directories that may contain 
       the file. returns the directory of the file 
       if found otherwise return None"""
    directories = []

    if file_type != -1: #to make sure it is not a folder
        file_name = file_name+file_type 
    #to examine name and type at the same time

    for root,dirs,files in os.walk(directory):
        #walk returns the (the directory inserted, a list of all sub-directories, a list of all names for the files in the directory)
        #The loop will help examine each and every sub-directories and all there sub-directories
        
        if file_name in files:
            directories.append( os.path.join(root,file_name) )
    return directories

def advanced_file_search(file_name, file_type, directory, extension_flag = 0, similarity_value = 0.8):
    #extension_flag when 0 it ignores extension difference and similarity_value sets the percentage for how the file names should be alike minimum shouldbe .5
    """searches for a file takes 3 arguments name of file, its type 
       and possible directories that may contain the file. returns #this needs to change
       the directory of the file if found otherwise return None"""
    directories = [] #will be returned at the end   

    for root,dirs,files in os.walk(directory):
            #walk returns the (the directory inserted, a list of all sub-directories, a list of all names for the files in the directory)
            #The loop will help examine each and every sub-directories and all there sub-directories
            for file in files:
                file_base, file_extension = os.path.splitext(file)
                temp_name = file_base+file_extension #concat. file name and its extension
                if file_name != "": #the similarities will work if there is a file name
                    
                    comparison_percentage = SequenceMatcher(None, file_base.lower(), file_name.lower()).ratio() #returns from 0 to 1 float 
                    #ratio returns the float value of the comparison between 0 and 1(0 for no similarity and 1 for exact match)

                    if comparison_percentage >= similarity_value and extension_flag and file_type != -1:
                        if file_extension == file_type: #make sure the extensions match
                            directories.append(os.path.join(root,temp_name)) #appends the directory of the found file

                    elif comparison_percentage >= similarity_value and not extension_flag and file_type != -1:
                            directories.append(os.path.join(root,temp_name))

                    elif comparison_percentage >= similarity_value and not extension_flag and file_type == -1: #means the function is looking for a folder
                            directories.append(os.path.join(root,temp_name))
                            #hmmm this part seems to be covered in the last elif

                else: #file name is an empty string meaning we will search for all files with a certain extension
                    if file_extension == file_type:
                        directories.append(os.path.join(root,temp_name))          
    return directories
