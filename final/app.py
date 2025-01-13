from flask import Flask, redirect, render_template, request, jsonify, url_for, send_from_directory
import os, pymysql
from db_connection import get_cursor
from edit import edit_clip
import shutil
import time

db = get_cursor()
cursor = db.cursor(pymysql.cursors.DictCursor)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'upload/source'


@app.route("/")
def home():
    print("[home]")
    return render_template('index.html')


@app.route("/index", methods=['GET'])
def index():
    print("[index]")
    videos = get_videos(limit=4)
    print(videos)
    return jsonify(videos), 200



def get_videos(limit, status_filter=None):
    print("func get_videos")
    try:
        query = "SELECT * FROM uploaded"
        query_params = ()
        
        # 如果有狀態過濾條件則添加條件
        if status_filter:
            query += " WHERE status = %s"
            query_params += (status_filter,)
        
        # 如果無限制條件則省略 LIMIT
        if limit is not None:
            query += " ORDER BY upload_time DESC LIMIT %s"
            query_params += (limit,)
        else:
            query += " ORDER BY upload_time DESC"

        cursor.execute(query, query_params)
        results = cursor.fetchall()
        return results
    
    except Exception as e:
        print(f"<get_videos> Error: {e}")
        return []
    
#    finally:
#        cursor.close()



# 存儲於 static 文件夾外部時，需要特別指定以訪問媒體文件 (flask)
@app.route('/upload/source/<path:filename>')
def uploaded_file(filename):
    print('upload/source', filename+".mp4") # 需要修正！從數據庫中讀取文件格式 
    return send_from_directory('upload/source', filename+".mp4")



@app.route('/upload', methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"<upload_file()> error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 保存文件
    file_name = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    try:
        # 如果文件夾不存在則創建
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        # 保存文件
        file.save(file_path)

        # 將文件信息保存到數據庫
        save_file_info_to_db(file_path)

        return redirect(url_for('home'))

    except Exception as e:
        print(f"<upload_file()> Error: {e}")
        return jsonify({"error": str(e)}), 500


def save_file_info_to_db(file_path):
    # 分離文件名和路徑
    directory, full_file_name = os.path.split(file_path)  # 分離目錄和文件名
    file_name, file_extension = os.path.splitext(full_file_name)  # 分離文件名和擴展名

    try:
        # 將信息保存到數據庫
        query = "INSERT INTO uploaded (file_path, file_name, format) VALUES (%s, %s, %s)"
        cursor.execute(query, (directory, file_name, file_extension))
        db.commit()
    except Exception as e:
        print(f"<save_file_info_to_db()> Database error: {e}")
#    finally:
#        cursor.close()



@app.route("/delete", methods=["POST"])
def delete_file():
    print("delete_file()")
    try:
        data = request.get_json()
        file_name = request.json.get('file_name')
        source = data.get("source")
        print(file_name)

        if not file_name:
            return jsonify({"<delete_file()> error": "File name not provided"}), 400


        cursor = db.cursor()


        # 從數據庫中獲取相關文件信息
        query = """
            SELECT file_id, file_path, file_name, format
            FROM uploaded
            WHERE file_name = %s
        """

        cursor.execute(query, (file_name,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"<delete_file()> error": "File not found in database"}), 404

        file_id, file_path, file_name, format = result  # 從數據庫中獲取路徑

    
        # 輸出文件路徑（用於調試）
        print(f"Deleting file: {file_path}/{file_name}")


        # 1. 從服務器實際刪除文件
        full_file_path = os.path.join(file_path, file_name+format)
        if os.path.exists(full_file_path):
            os.remove(full_file_path)
            print(f"File {full_file_path} deleted.")
        else:
            print(f"File {full_file_path} does not exist.")
        
        # 1-1. 刪除文件夾
        file_id_folder = os.path.join("upload", str(file_id))
        if os.path.exists(file_id_folder):
            shutil.rmtree(file_id_folder)  # 刪除整個目錄
            print(f"Directory deleted: {file_id_folder}")
        else:
            print(f"Directory not found: {file_id_folder}")
        


        # 2. 從 `edited` 表中刪除 source_id 與 file_id 相匹配的元組
        query_delete_edited = "DELETE FROM edited WHERE source_id = %s"
        cursor.execute(query_delete_edited, (file_id,))

        # 3. 從 `uploaded` 表中刪除對應元組
        query_delete_uploaded = "DELETE FROM uploaded WHERE file_id = %s"
        cursor.execute(query_delete_uploaded, (file_id,))

        # 提交更改
        db.commit()




        # 根據來源確定重定向路徑
        if source == "/library":
            redirect_url = url_for('library')  # 重定向到 library.html
        else:
            redirect_url = url_for('home')  # 默認重定向到 index.html

        return jsonify({"success": True, "redirect_url": redirect_url}), 200
    

    except Exception as e:
        print(f"<delete_file()> Error: {e}")
        return jsonify({"error": str(e)}), 500




@app.route("/library")
def library():
    print("[library]")
    return render_template('library.html')


@app.route("/getLibrary", methods=['GET'])
def getLibrary():
    print("[getLib]")
    videos = get_videos(limit=None)
    print(videos)
    return jsonify(videos), 200




@app.route('/cutVideo', methods=["POST"])
def cut_video():
    print("/cutVideo")
    data = request.get_json()
    url = data.get('url')
    filename = data.get('filename')

    print("url:", url, "file_name", filename)


    if not url or not filename:
        return jsonify({"error": "Missing url or filename"}), 400

    try:
        cursor = db.cursor()
        db.commit()

        # 從數據庫中查找匹配的元組
        query = """
            SELECT file_id, file_path, file_name, format, status, upload_time
            FROM uploaded
            WHERE file_path = %s AND file_name = %s
        """
        cursor.execute(query, (url, filename))
        result = cursor.fetchone()
        """
        result = (1, '/videos', 'video1.mp4', 'mp4', 'success', datetime.datetime(2024, 12, 5, 12, 0, 0))
        """

        if not result:
            return jsonify({"error": "No matching record found in database"}), 404

        file_id, file_path, file_name, format, status, upload_time = result

        # status == 0 : 未編輯
        if status == 0:
            print("not edited")
            edit_clip(result) # 將數據庫對象傳遞給編輯函數

        # status == 1 : 已完成編輯
        else:
            print(f"Status is {status}, already edited.")

        # 渲染 index.html
        return jsonify({
            "message": "Video edited successfully",
            "redirect_url": url_for('edited', sourcefile=file_name)
        }), 200

    except Exception as e:
        print(f"<cut_video> Database error: {e}")
        return jsonify({"error": str(e)}), 500

#    finally:
#        cursor.close()
    


@app.route('/edited/<sourcefile>')
def edited(sourcefile):
    print(f"/edited/{sourcefile}\n")
    try:

        db.commit()
        # 從 uploaded 表中獲取與 sourcefile 對應的 source_id
        cursor.execute("SELECT file_id FROM uploaded WHERE file_name = %s", (sourcefile,))
        source_id_row = cursor.fetchone()

        if not source_id_row:
            return jsonify({"message": "Source file not found"}), 404
        
        source_id = source_id_row["file_id"]

        # 從 edited 表中獲取與 source_id 對應的視頻
        cursor.execute(
            "SELECT clip_name, clip_path, format, clip_number FROM edited WHERE source_id = %s ORDER BY clip_number ASC",
            (source_id,)
        )
        clips = cursor.fetchall()

        # 構造 JSON 響應數據
        srcVideo_list = []
        for clip in clips:
            clip_info = {
                "filename": clip["clip_name"] + clip["format"],
                "url": f"/{clip['clip_path']}/{clip['clip_name']}{clip['format']}"
            }
            srcVideo_list.append(clip_info)
            print(clip_info)

        # 傳遞到模板
        return render_template('edited.html', videos=srcVideo_list)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": "Failed to fetch video list",
            "error": str(e)
        }), 500


@app.route('/upload/<file_id>/edited/<path:filename>')
def serve_file(file_id, filename):
    directory = f"upload/{file_id}/edited"
    return send_from_directory(directory, filename)



@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response



## 顯示模態彈出內容
@app.route("/get_clip_metadata", methods=["GET"])
def get_clip_metadata():
    # 從請求中獲取 filename
    filename = request.args.get("filename")

    if not filename:
        return jsonify({"error": "filename is required"}), 400

    db = get_cursor()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        filename = filename.rsplit(".", 1)[0] # 去掉擴展名

        # 從數據庫中獲取與該 filename 對應的 title 和 contents
        query = "SELECT title, contents FROM edited WHERE clip_name = %s"
        cursor.execute(query, (filename,))
        result = cursor.fetchone()

        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Metadata not found for the provided filename"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    #finally:
        #cursor.close()
        #db.close()




if __name__ == "__main__":
    app.run(debug=True)
