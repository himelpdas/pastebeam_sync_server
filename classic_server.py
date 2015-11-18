from functions import *
from bottle import Bottle, static_file

app = Bottle()

if os.name == "nt":
    UPLOAD_DIR = r"C:\Users\Himel\btsync\Coding\virtualenv\projects\PasteBeam\sync_server\.server"
else:
    UPLOAD_DIR = "/media/sf_btsync/Coding/virtualenv/projects/PasteBeam/sync_server/.server"


response.content_type = 'application/json'  # for http

@app.get('/file_exists/<filename>')
def file_exists(filename):
    response.content_type =  "application/json; charset=UTF8"

    file_path = os.path.join(UPLOAD_DIR,filename)
    file_exists = os.path.isfile(file_path)

    PRINT("file exists", file_exists)

    return json.dumps({"result":file_exists})

@app.post('/upload')
def handle_upload():
    #print "HANDLE HANDLE HANDLE"
    result = "OK"
    #save_path = UPLOAD_DIR

    upload    = request.files.get('upload')

    #name, ext = os.path.splitext(upload.filename)
    """
    if ext not in (".txt",'.bmp','.png','.jpg','.jpeg', '.py'):
        result = 'File extension not allowed.'
    else:
        upload.save(save_path, overwrite=False) # appends upload.filename automatically

    try:
        upload.save(save_path, overwrite=False) # appends upload.filename automatically
    except IOError:
        pass
    """
    grid_fs.put(upload.file, filename = upload.filename)

    response.content_type =  "application/json; charset=UTF8"
    return json.dumps({"upload_result":result})

@app.get('/static/<filename>')
def handle_download(filename):
    gridout = grid_fs.get_last_version(filename) #http://goo.gl/ioQXfh #this used to be handled by static_file, but we're directly making the fileobject response ourselves
    response.content_type = "application/octet-stream" #just in case, but not necessary since we're not using a browser
    response.content_length = gridout.length
    return gridout
    #return static_file(filename, root=UPLOAD_DIR)