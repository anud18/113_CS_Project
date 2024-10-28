from flask import Flask, redirect, render_template, request, jsonify, url_for
from edit import edit_clip
import os

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

    
    # 如果已經有剪過該影片 直接從edited_folder裡拿
    if os.path.isdir(f"{EDITED_FOLDER}/{only_video_name}"):
        print(f"{EDITED_FOLDER}/{only_video_name}")
        print("folder exists.")
        return jsonify({
            "message": "Video already edited",
            "redirect_url": url_for('edited', sourcefile=only_video_name)
        }), 200
    
    
    # 如果沒剪過的話 就剪片
    else:
        print(f"{EDITED_FOLDER}/{video_filename.split('.')[0]}")
        print("folder does not exist. go to edit_clip()\n")
        edited_filename = edit_clip(video_filename)
        return jsonify({
            "message": "Video edited successfully",
            "redirect_url": url_for('edited', sourcefile=only_video_name)
        }), 200



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







if __name__ == "__main__":
    app.run(debug=True)
