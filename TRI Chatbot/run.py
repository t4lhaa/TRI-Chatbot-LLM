import base64 
import hashlib 
import json 
import os 
import tempfile 
import time 
import uuid 
from pathlib import Path 

from flask import Flask ,Response ,jsonify ,request ,send_from_directory ,session 
from flask_cors import CORS 

import agent as tri_agent 

app =Flask (__name__ ,static_folder ="static")
app .secret_key =os .urandom (24 )
app .config ["MAX_CONTENT_LENGTH"]=50 *1024 *1024 
CORS (app ,supports_credentials =True )


_histories :dict ={}


UPLOAD_DIR =Path (tempfile .gettempdir ())/"tri_uploads"
UPLOAD_DIR .mkdir (exist_ok =True )


USERS_DIR =Path ("./users")
USERS_DIR .mkdir (exist_ok =True )
USERS_FILE =USERS_DIR /"users.json"

CHAT_HISTORY_DIR =Path ("./chat_history")
CHAT_HISTORY_DIR .mkdir (exist_ok =True )


ALLOWED_IMAGE_EXT ={".jpg",".jpeg",".png",".gif",".webp",".bmp"}

ALLOWED_TEXT_EXT ={
".txt",".md",".csv",".json",".xml",".yaml",".yml",".toml",".ini",".cfg",".conf",
".html",".htm",".css",".js",".ts",".jsx",".tsx",".vue",".svelte",
".c",".h",".cpp",".cc",".cxx",".hpp",".hxx",
".cs",".java",".rs",".go",".zig",
".py",".rb",".php",".pl",".lua",".r",".m",".sh",".bash",".zsh",".fish",".ps1",
".sql",".graphql",".proto",
".swift",".kt",".kts",".dart",".scala",".ex",".exs",".erl",".hs",".ml",
".f",".f90",".f95",".asm",".s",".makefile",".cmake",
}

ALLOWED_BINARY_EXT ={
".pdf",
".docx",".doc",
".xlsx",".xls",
".pptx",
}


def _hash_password (password :str )->str :
    return hashlib .sha256 (password .encode ("utf-8")).hexdigest ()


def load_users ()->dict :
    if not USERS_FILE .exists ():
        return {}
    try :
        with open (USERS_FILE ,"r",encoding ="utf-8")as f :
            return json .load (f )
    except Exception :
        return {}


def save_users (users :dict )->None :
    with open (USERS_FILE ,"w",encoding ="utf-8")as f :
        json .dump (users ,f ,ensure_ascii =False ,indent =2 )


def get_sessions_file (username :str )->Path :
    """Each user gets their own sessions JSON file inside chat_history/."""
    safe ="".join (c if c .isalnum ()or c in "-_"else "_"for c in username .lower ())
    return CHAT_HISTORY_DIR /f"chat_sessions_{safe }.json"

@app .route ("/auth/register",methods =["POST"])
def auth_register ():
    data =request .get_json (force =True )
    name =(data .get ("name")or "").strip ()
    age =data .get ("age")
    gender =(data .get ("gender")or "").strip ()
    username =(data .get ("username")or "").strip ().lower ()
    password =(data .get ("password")or "").strip ()

    if not all ([name ,age ,gender ,username ,password ]):
        return jsonify ({"error":"All fields are required."}),400 
    if len (username )<3 :
        return jsonify ({"error":"Username must be at least 3 characters."}),400 
    if len (password )<4 :
        return jsonify ({"error":"Password must be at least 4 characters."}),400 
    if not str (age ).isdigit ()or not (1 <=int (age )<=120 ):
        return jsonify ({"error":"Please enter a valid age."}),400 

    users =load_users ()
    if username in users :
        return jsonify ({"error":"Username already taken. Please choose another."}),409 

    users [username ]={
    "name":name ,
    "age":int (age ),
    "gender":gender ,
    "username":username ,
    "password":_hash_password (password ),
    "created_at":time .time (),
    }
    save_users (users )

    session ["username"]=username 
    session ["sid"]=str (uuid .uuid4 ())
    return jsonify ({"status":"registered","username":username ,"name":name })


@app .route ("/auth/login",methods =["POST"])
def auth_login ():
    data =request .get_json (force =True )
    username =(data .get ("username")or "").strip ().lower ()
    password =(data .get ("password")or "").strip ()

    if not username or not password :
        return jsonify ({"error":"Username and password are required."}),400 

    users =load_users ()
    user =users .get (username )
    if not user or user ["password"]!=_hash_password (password ):
        return jsonify ({"error":"Invalid username or password."}),401 

    session ["username"]=username 
    session ["sid"]=str (uuid .uuid4 ())
    return jsonify ({
    "status":"logged_in",
    "username":username ,
    "name":user ["name"],
    "age":user ["age"],
    "gender":user ["gender"],
    })


@app .route ("/auth/logout",methods =["POST"])
def auth_logout ():
    username =session .pop ("username",None )
    session .pop ("sid",None )
    return jsonify ({"status":"logged_out","username":username })


@app .route ("/auth/me",methods =["GET"])
def auth_me ():
    username =session .get ("username")
    if not username :
        return jsonify ({"authenticated":False }),401 
    users =load_users ()
    user =users .get (username )
    if not user :
        return jsonify ({"authenticated":False }),401 
    return jsonify ({
    "authenticated":True ,
    "username":username ,
    "name":user ["name"],
    "age":user ["age"],
    "gender":user ["gender"],
    })


@app .route ("/auth/users",methods =["GET"])
def auth_list_users ():
    """Return list of existing usernames (for the Switch User feature)."""
    users =load_users ()
    return jsonify ({
    "users":[
    {"username":u ,"name":v ["name"]}
    for u ,v in users .items ()
    ]
    })


def require_auth ():
    """Helper: returns (username, error_response). If error_response is not None, return it."""
    username =session .get ("username")
    if not username :
        return None ,(jsonify ({"error":"Not authenticated"}),401 )
    return username ,None 

def get_history (username :str )->list :
    if username not in _histories :
        _histories [username ]=[]
    return _histories [username ]

def _allowed_file (filename :str )->tuple [bool ,str ]:
    ext =Path (filename ).suffix .lower ()
    base =Path (filename ).name .lower ()
    if base in ("makefile","dockerfile","gemfile","procfile","rakefile"):
        return True ,"text"
    if ext in ALLOWED_IMAGE_EXT :
        return True ,"image"
    if ext in ALLOWED_TEXT_EXT :
        return True ,"text"
    if ext in ALLOWED_BINARY_EXT :
        return True ,"binary"
    return False ,"unknown"


def _extract_pdf (path :Path )->str :
    try :
        import fitz 
        doc =fitz .open (str (path ))
        pages =[]
        for i ,page in enumerate (doc ):
            text =page .get_text ("text")
            if text .strip ():
                pages .append (f"[Page {i +1 }]\n{text .strip ()}")
        doc .close ()
        return "\n\n".join (pages )if pages else "[PDF contained no extractable text]"
    except ImportError :
        return "[PDF extraction requires PyMuPDF: pip install PyMuPDF]"
    except Exception as e :
        return f"[PDF extraction error: {e }]"


def _extract_docx (path :Path )->str :
    try :
        from docx import Document 
        doc =Document (str (path ))
        parts =[]
        for para in doc .paragraphs :
            if para .text .strip ():
                parts .append (para .text )
        for table in doc .tables :
            for row in table .rows :
                row_texts =[cell .text .strip ()for cell in row .cells if cell .text .strip ()]
                if row_texts :
                    parts .append (" | ".join (row_texts ))
        return "\n".join (parts )if parts else "[Document contained no readable text]"
    except ImportError :
        return "[DOCX extraction requires python-docx: pip install python-docx]"
    except Exception as e :
        return f"[DOCX extraction error: {e }]"


def _extract_excel (path :Path )->str :
    ext =path .suffix .lower ()
    try :
        if ext ==".xlsx":
            import openpyxl 
            wb =openpyxl .load_workbook (str (path ),read_only =True ,data_only =True )
            lines =[]
            for sheet_name in wb .sheetnames :
                ws =wb [sheet_name ]
                lines .append (f"=== Sheet: {sheet_name } ===")
                for row in ws .iter_rows (values_only =True ):
                    row_vals =[str (v )if v is not None else ""for v in row ]
                    if any (v .strip ()for v in row_vals ):
                        lines .append ("\t".join (row_vals ))
            wb .close ()
            return "\n".join (lines )if lines else "[Spreadsheet contained no data]"
        elif ext ==".xls":
            import xlrd 
            wb =xlrd .open_workbook (str (path ))
            lines =[]
            for sheet in wb .sheets ():
                lines .append (f"=== Sheet: {sheet .name } ===")
                for rx in range (sheet .nrows ):
                    row_vals =[str (sheet .cell_value (rx ,cx ))for cx in range (sheet .ncols )]
                    if any (v .strip ()for v in row_vals ):
                        lines .append ("\t".join (row_vals ))
            return "\n".join (lines )if lines else "[Spreadsheet contained no data]"
    except ImportError as ie :
        pkg ="openpyxl"if ext ==".xlsx"else "xlrd"
        return f"[Excel extraction requires {pkg }: pip install {pkg }]"
    except Exception as e :
        return f"[Excel extraction error: {e }]"
    return "[Unsupported Excel format]"


def _extract_pptx (path :Path )->str :
    try :
        from pptx import Presentation 
        prs =Presentation (str (path ))
        lines =[]
        for i ,slide in enumerate (prs .slides ):
            lines .append (f"=== Slide {i +1 } ===")
            for shape in slide .shapes :
                if hasattr (shape ,"text")and shape .text .strip ():
                    lines .append (shape .text .strip ())
        return "\n".join (lines )if lines else "[Presentation contained no readable text]"
    except ImportError :
        return "[PPTX extraction requires python-pptx: pip install python-pptx]"
    except Exception as e :
        return f"[PPTX extraction error: {e }]"


def _extract_binary (path :Path ,ext :str )->str :
    if ext ==".pdf":
        return _extract_pdf (path )
    elif ext in (".docx",".doc"):
        return _extract_docx (path )
    elif ext in (".xlsx",".xls"):
        return _extract_excel (path )
    elif ext ==".pptx":
        return _extract_pptx (path )
    return "[Unsupported binary format]"


def _handle_upload (file )->dict |None :
    if not file or not file .filename :
        return None 
    ok ,ftype =_allowed_file (file .filename )
    if not ok :
        return None 
    ext =Path (file .filename ).suffix .lower ()
    tmp_name =f"{uuid .uuid4 ().hex }{ext }"
    tmp_path =UPLOAD_DIR /tmp_name 
    file .save (str (tmp_path ))

    if ftype =="image":
        mime_map ={".jpg":"image/jpeg",".jpeg":"image/jpeg",
        ".png":"image/png",".gif":"image/gif",
        ".webp":"image/webp",".bmp":"image/bmp"}
        mime_type =mime_map .get (ext ,"image/jpeg")
        with open (tmp_path ,"rb")as f :
            b64 =base64 .b64encode (f .read ()).decode ("utf-8")
        return {"type":"image","filename":file .filename ,
        "filepath":str (tmp_path ),"base64":b64 ,"mime_type":mime_type }

    elif ftype =="binary":
        content =_extract_binary (tmp_path ,ext )
        char_limit =12000 
        truncated =len (content )>char_limit 
        label_map ={".pdf":"PDF document",".docx":"Word document",".doc":"Word document",
        ".xlsx":"Excel spreadsheet",".xls":"Excel spreadsheet",
        ".pptx":"PowerPoint presentation"}
        return {"type":"text","filename":file .filename ,"filepath":str (tmp_path ),
        "content":content [:char_limit ],"truncated":truncated ,
        "doc_type":label_map .get (ext ,"document")}

    else :
        try :
            content =tmp_path .read_text (encoding ="utf-8",errors ="replace")
        except Exception :
            content =tmp_path .read_text (encoding ="latin-1",errors ="replace")
        char_limit =8000 
        return {"type":"text","filename":file .filename ,"filepath":str (tmp_path ),
        "content":content [:char_limit ],"truncated":len (content )>char_limit }

def load_chat_sessions (username :str )->list :
    f =get_sessions_file (username )
    if not f .exists ():
        return []
    try :
        with open (f ,"r",encoding ="utf-8")as fp :
            data =json .load (fp )
        return data if isinstance (data ,list )else []
    except Exception as e :
        print (f"[Sessions] Failed to load for {username }: {e }")
        return []


def save_chat_sessions (username :str ,sessions :list )->None :
    try :
        with open (get_sessions_file (username ),"w",encoding ="utf-8")as fp :
            json .dump (sessions ,fp ,ensure_ascii =False ,indent =2 )
    except Exception as e :
        print (f"[Sessions] Failed to save for {username }: {e }")


@app .route ("/")
def index ():
    return send_from_directory (".","index.html")


@app .route ("/chat",methods =["POST"])
def chat ():
    username ,err =require_auth ()
    if err :
        return err 

    if request .content_type and "multipart"in request .content_type :
        msg =(request .form .get ("message")or "").strip ()
        file =request .files .get ("file")
    else :
        data =request .get_json (force =True )
        msg =(data .get ("message")or "").strip ()
        file =None 

    if not msg and not file :
        return jsonify ({"error":"Empty message"}),400 

    history =get_history (username )
    start =time .time ()
    file_context =_handle_upload (file )if file else None 

    try :
        result =tri_agent .agent (msg ,history ,file_context =file_context ,username =username )
    except Exception as e :
        return jsonify ({"error":str (e )}),500 

    return jsonify ({
    "answer":result ["answer"],
    "steps":result ["steps"],
    "tools":[t ["tool"]for t in result ["tool_calls"]],
    "elapsed":round (time .time ()-start ,1 ),
    "status":result ["status"],
    })


@app .route ("/paste-image",methods =["POST"])
def paste_image ():
    username ,err =require_auth ()
    if err :
        return err 

    data =request .get_json (force =True )
    data_url =data .get ("dataUrl","")
    if not data_url .startswith ("data:image/"):
        return jsonify ({"error":"Invalid image data"}),400 

    try :
        header ,b64_data =data_url .split (",",1 )
        mime_type =header .split (":")[1 ].split (";")[0 ]
        ext_map ={"image/png":".png","image/jpeg":".jpg","image/gif":".gif",
        "image/webp":".webp","image/bmp":".bmp"}
        ext =ext_map .get (mime_type ,".png")
        raw =base64 .b64decode (b64_data )
        tmp_name =f"{uuid .uuid4 ().hex }{ext }"
        tmp_path =UPLOAD_DIR /tmp_name 
        tmp_path .write_bytes (raw )
    except Exception as e :
        return jsonify ({"error":f"Image decode error: {e }"}),400 

    file_context ={"type":"image","filename":f"pasted-image{ext }",
    "filepath":str (tmp_path ),"base64":b64_data ,"mime_type":mime_type }
    token =uuid .uuid4 ().hex 
    _paste_store [token ]=file_context 
    return jsonify ({"token":token })


_paste_store :dict ={}


@app .route ("/stream",methods =["GET","POST"])
def stream ():
    username ,err =require_auth ()
    if err :
        return err 

    file =None 
    paste_token =None 

    if request .method =="POST":
        ct =request .content_type or ""
        if "multipart"in ct :
            msg =(request .form .get ("message")or "").strip ()
            file =request .files .get ("file")
        else :
            body =request .get_json (force =True )or {}
            msg =(body .get ("message")or "").strip ()
            paste_token =body .get ("pasteToken")
    else :
        msg =(request .args .get ("message")or "").strip ()

    if not msg and not file and not paste_token :
        return jsonify ({"error":"Empty message"}),400 

    history =get_history (username )

    if paste_token and paste_token in _paste_store :
        file_context =_paste_store .pop (paste_token )
    elif file :
        file_context =_handle_upload (file )
    else :
        file_context =None 

    def generate ():
        try :
            for event in tri_agent .agent_streaming (msg ,history ,
            file_context =file_context ,
            username =username ):
                payload =json .dumps (event )
                yield f"data: {payload }\n\n"
        except Exception as e :
            err_payload =json .dumps ({"event":"error","data":{"message":str (e )}})
            yield f"data: {err_payload }\n\n"
        yield 'data: {"event": "done"}\n\n'

    return Response (
    generate (),
    mimetype ="text/event-stream",
    headers ={"Cache-Control":"no-cache","X-Accel-Buffering":"no"},
    )


@app .route ("/memory",methods =["GET"])
def memory_info ():
    username =session .get ("username")
    count =tri_agent .get_memory_count (username )
    samples =[]
    for doc ,meta in tri_agent .get_memory_samples (limit =5 ,username =username ):
        samples .append ({
        "text":doc [:120 ]+("..."if len (doc )>120 else ""),
        "source":meta .get ("source","?"),
        })
    return jsonify ({"chunks":count ,"samples":samples })


@app .route ("/clear",methods =["POST"])
def clear_history ():
    username =session .get ("username")
    if username and username in _histories :
        _histories [username ]=[]
    return jsonify ({"status":"cleared"})

@app .route ("/sessions",methods =["GET"])
def get_sessions ():
    username ,err =require_auth ()
    if err :
        return err 
    sessions =load_chat_sessions (username )
    return jsonify ({"sessions":sessions })


@app .route ("/sessions",methods =["POST"])
def save_sessions ():
    username ,err =require_auth ()
    if err :
        return err 
    data =request .get_json (force =True )
    sessions =data .get ("sessions",[])
    if not isinstance (sessions ,list ):
        return jsonify ({"error":"sessions must be a list"}),400 
    save_chat_sessions (username ,sessions )
    return jsonify ({"status":"saved","count":len (sessions )})


@app .route ("/sessions/<session_id>",methods =["DELETE"])
def delete_session (session_id :str ):
    username ,err =require_auth ()
    if err :
        return err 
    sessions =load_chat_sessions (username )
    original_len =len (sessions )
    sessions =[s for s in sessions if s .get ("id")!=session_id ]
    save_chat_sessions (username ,sessions )
    deleted =original_len -len (sessions )
    return jsonify ({"status":"deleted","deleted":deleted })

if __name__ =="__main__":
    print ("\n"+"="*58 )
    print ("  TRI Chatbot - Web Server")
    print ("  Open:  http://localhost:5000")
    print ("  Stop:  Ctrl + C")
    print (f"  Users file:       {USERS_FILE .resolve ()}")
    print (f"  Chat history dir: {CHAT_HISTORY_DIR .resolve ()}")
    print ("  Auth: /auth/register  /auth/login  /auth/logout")
    print ("="*58 +"\n")
    app .run (host ="0.0.0.0",port =5000 ,debug =False ,threaded =True )
