from flask import Flask, redirect, render_template, request, jsonify, url_for
from edit import edit_clip
import os
import shutil #刪除資料夾

app = Flask(__name__)

# 儲存路徑
SOURCE_FOLDER = 'static/source'
EDITED_FOLDER = 'static/video'

@app.route("/")
def index():
    print("///")
    return render_template('index.html')

@app.route("/index")
def get_all_videos():
    print("indexxxxxx")
    try:
        # 拿SOURCE_FOLDER中的所有檔案
        srcVideo_files = os.listdir(SOURCE_FOLDER)
        srcVideo_list = []

        # 把上面的拿到的所有影片資訊製成json格式
        for video in srcVideo_files:
            video_info = {
                "filename": video,
                "url": f"/{SOURCE_FOLDER}/{video}"  # 影片的url
            }
            srcVideo_list.append(video_info)

        return jsonify({
            "message": "srcVideo list fetched successfully",
            "videos": srcVideo_list
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Failed to fetch video list",
            "error": str(e)
        }), 500
    


@app.route("/upload", methods=["POST"]) 
def upload():
    if request.method == "POST":
        # save uploaded video
        srcVideo = request.files["file"]
        srcVideo_path = f"{SOURCE_FOLDER}/{srcVideo.filename}"
        srcVideo.save(f"{srcVideo_path}")

        
    return redirect(url_for('index'))


@app.route('/cutVideo', methods=['POST'])
def cutVideo():
    print("/cutVideo\n")
    data = request.get_json()
    video_url = data.get('url') # ex. /static/source/test.mp4
    video_filename = data.get('filename') # ex. test.mp4
    only_video_name = video_filename.split('.')[0]

    # test
    print(f"Received Video URL: {video_url}")
    print(f"Received Video Filename: {video_filename}")
    
    # 設定編輯後的資料夾路徑
    edited_folder_path = f"{EDITED_FOLDER}/{only_video_name}"
    
    # 如果資料夾已存在，檢查資料夾是否包含影片
    if os.path.isdir(edited_folder_path):
        print(f"{edited_folder_path} exists.")
        # 獲取資料夾內的影片檔案列表
        existing_files = os.listdir(edited_folder_path)
        video_files = [file for file in existing_files if file.endswith('.mp4')]

        if video_files:
            # 如果資料夾內有影片，直接提取
            print("Folder exists and contains video(s). Returning existing video(s).")
            return redirect(url_for('edited', sourcefile=only_video_name))
        else:
            # 資料夾存在但沒有影片
            print("Folder exists but no videos found. Proceeding to clip and save new video.")
            edited_filename = edit_clip(video_filename)
    else:
        # 資料夾不存在，創建資料夾並進行影片剪輯
        print(f"Folder {edited_folder_path} does not exist. Creating folder and proceeding to clip video.")
        os.makedirs(edited_folder_path)
        edited_filename = edit_clip(video_filename)

    return jsonify({"message": "Video info received successfully","filename": edited_filename}),200


@app.route('/edited/<sourcefile>')
def edited(sourcefile):
    print(f"/edited/{sourcefile}\n")
    try:
        
        # 拿SOURCE_FOLDER中的所有檔案
        editVideo_files = os.listdir(f"{EDITED_FOLDER}/{sourcefile}")
        print(f"check: {EDITED_FOLDER}/{sourcefile}\n")
        srcVideo_list = []

        
        # 把上面的拿到的所有影片資訊製成json格式
        for video in editVideo_files:
            video_info = {
                "filename": video,
                "url": f"/{EDITED_FOLDER}/{sourcefile}/{video}" 
            }
            srcVideo_list.append(video_info)
            print(video_info)


        # -> cutVideo()로 감
        # 整個函數是被cutVideo()呼叫
        return jsonify({
            "message": "srcVideo list fetched successfully",
            "videos": srcVideo_list
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Failed to fetch video list",
            "error": str(e)
        }), 500
        

#刪除紐
@app.route('/delete_video', methods=['POST'])
def delete_video():
    data = request.get_json()
    filename = data.get('filename')

    try:
        # 刪除 SOURCE_FOLDER 中的影片
        source_path = os.path.join(SOURCE_FOLDER, filename)
        if os.path.exists(source_path):
            os.remove(source_path)

        # 刪除 EDITED_FOLDER 中的影片資料夾
        edited_folder_path = os.path.join(EDITED_FOLDER, filename.split('.')[0])
        if os.path.exists(edited_folder_path):
            shutil.rmtree(edited_folder_path)

        return jsonify({"message": f"{filename} 刪除成功"}), 200

    except Exception as e:
        return jsonify({"message": "刪除影片失敗", "error": str(e)}), 500






if __name__ == "__main__":
    app.run(debug=True)