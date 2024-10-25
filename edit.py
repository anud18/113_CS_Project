import re
import os
import subprocess
from difflib import SequenceMatcher
from openai import OpenAI
import whisper
import time
from dotenv import load_dotenv


def cut_video(input_video, start, end, output_video):
    command = [
        "ffmpeg", "-i", input_video, 
        "-ss", start.split(',')[0], "-to", end.split(',')[0], 
        "-c:v copy -c:a copy",output_video,".mp4"
    ]

    print("FFmpeg command:", command)
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

 
def edit_clip(imgName): #img.filename (test.mp4) file+extension進來
    # 시간 측정 計時程式跑多久
    start_time = float(time.time())
    print(f"start time: {start_time}\n")
    print(f"editclip() filename:{imgName}")


    # Remove the file extension (test.mp4 -> test) 拿掉extension，只拿filename
    original_filename = os.path.splitext(imgName)[0]
    # Create folder name (static/video/test) folder name 為 file name的路徑
    output_folder = os.path.join("static/video/", original_filename)

    # Create the output folder if it doesn't exist 如果沒有folder，新增folder name 為 file name
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    

    # clip할 파일 경로 要剪片的 file 路徑
    input_file_path = os.path.join("static/source/", imgName) # (static/video/test.mp4)




    #whisper
    model = whisper.load_model("base")
    result = model.transcribe(input_file_path)
    
    #把srt轉成以下形式供分段使用
    segments_list = []
    """ 예시: 튜플 형식으로 저장
        segments_list = [
            ("00:00:00,000", "00:00:02,000", "안녕하세요"), [0][1][2]
            ("00:00:02,000", "00:00:05,000", "오늘은 좋은 날입니다"), [0][1][2]
            # ...
        ] 
    """

    #把segments_list轉成.txt 一個index一行
    with open(original_filename+".txt", "w", encoding="utf-8") as txt_file:
        for segment in result["segments"]:
            txt_file.write(segment["text"] + "\n")

    #srt
    with open(original_filename+".srt", "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(result["segments"]):
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]
            
            # timestamp format 轉換
            start_time = f"{int(start // 3600):02}:{int((start % 3600) // 60):02}:{int(start % 60):02},{int((start - int(start)) * 1000):03}"
            end_time = f"{int(end // 3600):02}:{int((end % 3600) // 60):02}:{int(end % 60):02},{int((end - int(end)) * 1000):03}"

            # 以srt形式處存
            srt_file.write(f"{i + 1}\n{start_time} --> {end_time}\n{text}\n\n")
            
            # 把上兩步結果存到segments_list中
            segments_list.append((start_time, end_time, text))
            
    #之後可以寫exception
    print("TXT SRT 新增成功   ")
    
    
    ##gpt 分段
    #從segments_list裡拿[2](文字)
    text_list = [segment[2] for segment in segments_list]

    #check(之後刪掉)
    print("--------------")
    #print(text_list)
    """ text_list eg.
    ['1950代初期 台灣所處的環境十分惡劣', '我們政府剛從大陸戳敗下來', '證據部門人性狂惘'] """
    print("--------------")


    #餵給gpt的問題
    gpt_input = ""
    for i in range(len(text_list)):
        gpt_input += text_list[i]+"\n"
    """eg.
    gpt_input===
    1950代初期 台灣所處的環境十分惡劣
    我們政府剛從大陸戳敗下來
    證據部門人性狂惘
    """
    gpt_input +="\n\n請你依據内容幫我分段列出那一段的内容 然後每段的開頭都要注記那一段的主題是什麽。你不能自己增加内容，只能依據我給你的文本。"


    prompt = f"你是一位負責把文章分段的機器人，必須要將使用者給的文本依內容分成好幾段。不能擅自增加段落內容的標點符號 段落內容中每句話都已\n分隔。每段請以 '[段落摘要]\n摘要\n[段落內容]\n內容\n' 的格式輸出：\n\n{gpt_input}"
    
    
    #Openai api呼叫
    load_dotenv()
    API_KEY = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=API_KEY)

    completion = client.chat.completions.create(
        model = "gpt-4o",

        messages = [
            
            {"role": "user", "content": prompt}

        ]   

    )
    
    #分段完結果gpt_output
    gpt_output = completion.choices[0].message.content
    

    #check(要刪)
    print(gpt_output) #gpt分段的結果
    print("gpt 分段完成")
    
    
    #存摘要、內容的list
    titles = []
    contents = []    
    
    
    #依[段落摘要][段落內容]切割分段結果
    matches = re.findall(r"\[段落摘要\]\n(.*?)\n\[段落內容\]\n(.*?)(?=\[段落摘要\]|\Z)", gpt_output, re.DOTALL)
    
    #分割完後存到titles、contents
    for match in matches:
        titles.append(match[0].strip())   # 요약 부분 (段落摘要)
        contents.append(match[1].strip())  # 내용 부분 (段落內容)
    
    print(f"titles:{titles}")
    print(f"contents:{contents}")
    print("matches储存完成\n")
            
    #處存每段文字開頭結尾的timestamp
    #會依照這個list剪輯        
    paragraph_timestamps = []
    
    #開始按照分段內容到segments_list中找開頭跟結尾的timestamp
    for paragraph in contents:
        print(f"paragraph:{paragraph}")
        start_timestamp = None
        end_timestamp = None
        current_text = ""  #這個段落目前為止掃到的內容
        
        for segment in segments_list:
            print(f"for {segment} in segments_list")
            _, end_time, segment_text = segment #把segment的內容分別存到這3個變數
            
            # segment_text在此paragrah的話 就進去
            if segment_text in paragraph:
                print("if in 2nd for")                  

                if start_timestamp is None:
                    # 如果現在還沒有拿到段落開頭的timestamp 就取
                    start_timestamp = segment[0]
                    print(f"new start_ts:::{start_timestamp}\n")
                
                # 把現在的segment_text放到current_text裡
                current_text += segment_text+"\n"
                #現在segment_text的end_time更新到end_ts
                end_timestamp = end_time 

                print(f"current_txt::{current_text}\n=============\n")
                print(f"end_ts for now :::{end_timestamp}")

                #如果current_text跟paragraph已經依樣 就break 到下一段落
                if paragraph.startswith(current_text):
                    print("paragraph end")
                    break
            
            
        
        if start_timestamp and end_timestamp:
            paragraph_timestamps.append((start_timestamp, end_timestamp))
            print(f"start ts:{start_timestamp}, end ts:{end_timestamp}") #測試用

    
            
    for i, (start, end) in enumerate(paragraph_timestamps):
        print(f"第{i+1}個 段落: 開始時間 = {start.split(',')[0]}, 結束時間 = {end.split(',')[0]}")
    # cut_video(original_mp4_path,start,end,i)
        terminal_command = "ffmpeg -i "+input_file_path+" -ss "+start.split(',')[0]+" -to "+end.split(',')[0]+" -c:v copy -c:a copy "+output_folder+"/"+titles[i]+".mp4"
        3
        
        os.system(terminal_command)
            
            
    """
    command = [
        "ffmpeg",
        "-i", file_path,         # Input video
        "-ss", start_time,        # Start time
        "-to", end_time,          # End time
        "-c:v", "copy",           # Copy video codec
        "-c:a", "copy",           # Copy audio codec
        output_path               # Output video
    ]
    

    # Execute the FFmpeg command
    try:
        subprocess.run(command, check=True)
        print(f"Video has been cut and saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while cutting the video: {e}")

    """

    return imgName