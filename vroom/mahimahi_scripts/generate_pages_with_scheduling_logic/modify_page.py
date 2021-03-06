import os
import sys
import subprocess
import common_module

# recorded folder to be copied and rewritten
recorded_folder = sys.argv[1]
rewritten_folder = sys.argv[2]
index = sys.argv[3]
page = sys.argv[4]

# temp folder to store rewritten protobufs
os.system("rm -rf rewritten_" + index)
os.system( "cp -r " + recorded_folder + " rewritten_" + index )

files = os.listdir("rewritten_" + index)

# iterate through files to get top-level HTML (must do this before processing files!)
found_top_level_html = False
top_files = []
top_file_to_top_level_html = dict()
for filename in files:
    top_cmd = "./protototext rewritten_" + index + "/" + filename + " top_level_temp_" + index
    proc_top = subprocess.Popen([top_cmd], stdout=subprocess.PIPE, shell=True)
    (out_top, err_top) = proc_top.communicate()
    out_top = out_top.strip("\n")
    top_level_html = out_top.split("na--me=")[1]
    if common_module.escape_page(top_level_html) == page:
        top_files.append(filename)
        top_file_to_top_level_html[filename] = top_level_html
        found_top_level_html = True
    os.system("rm top_level_temp_" + index)

print "FOUND TOP LEVEL: " + str(top_files)

if ( not found_top_level_html ): # didn't find top level HTML file
    print "Didn't find top-level HTML file in: " + recorded_folder
    os.system("rm -r rewritten_" + index + "/")
    exit()

for filename in files:
    # print filename

    #os.system("changeheader rewritten_" + index + "/" + filename + " Access-Control-Allow-Origin *")

    # convert response in protobuf to text (ungzip if necessary)
    command = "./protototext rewritten_" + index + "/" + filename + " rewritten_" + index + "/tempfile"
    proc = subprocess.Popen([command], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    return_code = proc.returncode
    out = out.strip("\n")
    # print out
    res_type = out.split("*")[0].split("=")[1]
    gzip = out.split("*")[2].split("=")[1]
    chunked = out.split("*")[1].split("=")[1]
    # need to still handle if response is chunked and gzipped (we can't just run gzip on it)!
    if ( ("html" in res_type) or ("javascript" in res_type) ): # html or javascript file, so rewrite
        if ( "true" in chunked ): # response chunked so we must unchunk
            os.system( "python unchunk.py rewritten_" + index + "/tempfile rewritten_" + index + "/tempfile1" )
            os.system( "mv rewritten_" + index + "/tempfile1 rewritten_" + index + "/tempfile" )
            # remove transfer-encoding chunked header from original file since we are unchunking
            os.system( "./removeheader rewritten_" + index + "/" + filename + " Transfer-Encoding" )
        if ( "false" in gzip ): # html or javascript but not gzipped
            if ( "javascript" in res_type ):
                os.system('cp get_unimportant_urls.js rewritten_' + index + '/prependtempfile')
                os.system('cat rewritten_' + index + '/tempfile >> rewritten_' + index + '/prependtempfile')
                os.system('mv rewritten_' + index + '/prependtempfile rewritten_' + index + '/tempfile')

            if ( "html" in res_type ): # rewrite all inline js in html files
                if ( filename in top_files ):
                    os.system('python html_rewrite.py rewritten_' + index + '/tempfile rewritten_' + index + '/htmltempfile "' + top_file_to_top_level_html[filename] + '"')
                    os.system('mv rewritten_' + index + '/htmltempfile rewritten_' + index + '/tempfile')

            # get new length of response
            size = os.path.getsize('rewritten_' + index + '/tempfile') - 1

            # convert modified file back to protobuf
            os.system( "./texttoproto rewritten_" + index + "/tempfile rewritten_" + index + "/" + filename )

            # add access control header to response
            #os.system("changeheader rewritten_" + index + "/" + filename + " Access-Control-Allow-Origin *")

            # add new content length header
            os.system( "./changeheader rewritten_" + index + "/" + filename + " Content-Length " + str(size) )
        else: # gzipped
            os.system("gzip -d -c rewritten_" + index + "/tempfile > rewritten_" + index + "/plaintext")
            if ( "javascript" in res_type ):
                os.system('cp get_unimportant_urls.js rewritten_' + index + '/prependtempfile')
                os.system('cat rewritten_' + index + '/plaintext >> rewritten_' + index + '/prependtempfile')
                os.system('mv rewritten_' + index + '/prependtempfile rewritten_' + index + '/plaintext')

            if ( "html" in res_type ): # rewrite all inline js in html files
                if ( filename in top_files ):
                    os.system('python html_rewrite.py rewritten_' + index + '/plaintext rewritten_' + index + '/htmltempfile "' + top_level_html + '"')
                    os.system('mv rewritten_' + index + '/htmltempfile rewritten_' + index + '/plaintext')

            # after modifying plaintext, gzip it again (gzipped file is 'finalfile')
            os.system( "gzip -c rewritten_" + index + "/plaintext > rewritten_" + index + "/finalfile" )

            # get new length of response
            size = os.path.getsize('rewritten_' + index + '/finalfile')

            # convert modified file back to protobuf
            os.system( "./texttoproto rewritten_" + index + "/finalfile rewritten_" + index + "/" + filename )

            # add new content length header to the newly modified protobuf (name is filename)
            os.system( "./changeheader rewritten_" + index + "/" + filename + " Content-Length " + str(size) )

            # add access control header to response
            #os.system("changeheader rewritten_" + index + "/" + filename + " Access-Control-Allow-Origin *")

            # delete temp files
            os.system("rm rewritten_" + index + "/plaintext")
            os.system("rm rewritten_" + index + "/finalfile")
        
    # delete original tempfile
    os.system("rm rewritten_" + index + "/tempfile")

os.system("mv rewritten_" + index + " " + rewritten_folder)

for filename in files:
    os.system("./changeheader " + rewritten_folder + "/" + filename + " Access-Control-Allow Origin *")
    os.system("./changeheader " + rewritten_folder + "/" + filename + " Access-Control-Allow-Headers Access-Control-Expose-Headers")
    os.system("./changeheader " + rewritten_folder + "/" + filename + " Access-Control-Expose-Headers 'Link, x-systemname-unimportant'")
