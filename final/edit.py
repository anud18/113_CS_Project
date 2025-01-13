import re
import os, pymysql
import subprocess
from difflib import SequenceMatcher
from openai import OpenAI
import whisper
import time
from dotenv import load_dotenv
from db_connection import get_cursor


def edit_clip(tuple):  # img.filename (test.mp4) file+extension進來 文件+擴展名進入
    print("edit_clip ", tuple)

    file_id, file_path, file_name, format, status, upload_time = tuple
    print("\n", file_id, file_path, file_name, format, status, upload_time, "\n")

    start_time = float(time.time())
    print(f"開始時間: {start_time}")

    # 基於 file_id 的基本路徑 (upload/20,30 等等)
    output_folder = os.path.join("upload/", str(file_id))

    # 如果資料夾不存在則創建資料夾
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        os.makedirs(output_folder + "/words")
        os.makedirs(output_folder + "/edited")

    output_folder_words = os.path.join(output_folder, "words")
    output_folder_edited = os.path.join(output_folder, "edited")

    # 原始文件路徑 (upload/編號/source)
    input_file = os.path.join(file_path, file_name + format)

    print(output_folder, "\n")
    print("input_folder:", input_file)



    # 如果 srt 和 txt 已經存在則跳過
    required_files = [file_name + ".txt", file_name + ".srt"]

    all_files_exist = all(os.path.isfile(os.path.join(output_folder_words, file)) for file in required_files)

    segments_list = []  # 初始化


    # 檢查文件是否存在
    if all_files_exist:
        # 如果文件已存在，從現有文件加載 segment_list
        print("文件已存在")

        # 從現有 TXT 文件讀取數據並加入 segments_list
        try:
            with open(os.path.join(output_folder_words, file_name + ".srt"), "r", encoding="utf-8") as srt_file:
                content = srt_file.read().strip()
                blocks = content.split("\n\n")
                for block in blocks:
                    lines = block.split("\n")
                    if len(lines) >= 3:
                        time_range = lines[1]  # 例如: 00:00:01,000 --> 00:00:05,000
                        start_time, end_time = time_range.split(" --> ")
                        text = lines[2]
                        segments_list.append((start_time.strip(), end_time.strip(), text.strip()))
        except IOError as e:
            print(f"讀取 SRT 文件時發生錯誤: {e}")

    else:
        print("文件不存在")
        try:
            # 加載 Whisper 模型
            model = whisper.load_model("base")
            result = model.transcribe(input_file)

            # 創建保存結果的目錄
            save_path = os.path.join(output_folder_words)
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # 創建 TXT 文件
            try:
                with open(os.path.join(save_path, file_name + ".txt"), "w", encoding="utf-8") as txt_file:
                    for segment in result["segments"]:
                        txt_file.write(segment["text"] + "\n")
            except IOError as e:
                print(f"創建 TXT 文件時發生錯誤: {e}")

            # 創建 SRT 文件
            try:
                with open(os.path.join(save_path, file_name + ".srt"), "w", encoding="utf-8") as srt_file:
                    for i, segment in enumerate(result["segments"]):
                        start = segment["start"]
                        end = segment["end"]
                        text = segment["text"]

                        # 轉換時間戳格式
                        start_time = f"{int(start // 3600):02}:{int((start % 3600) // 60):02}:{int(start % 60):02},{int((start - int(start)) * 1000):03}"
                        end_time = f"{int(end // 3600):02}:{int((end % 3600) // 60):02}:{int(end % 60):02},{int((end - int(end)) * 1000):03}"

                        # 撰寫 SRT 文件
                        srt_file.write(f"{i + 1}\n{start_time} --> {end_time}\n{text}\n\n")

                        # 更新 segments_list
                        segments_list.append((start_time, end_time, text))
            except IOError as e:
                print(f"創建 SRT 文件時發生錯誤: {e}")

            print("成功生成 TXT 和 SRT 文件")

        except whisper.exceptions.WhisperError as e:
            print(f"Whisper 模型處理時發生錯誤: {e}")

        except Exception as e:
            print(f"發生未知錯誤: {e}")


##### gpt 分段 ####
    print("開始 GPT 分段")

    # 從 segments_list 提取 [2] (文字)
    text_list = [segment[2] for segment in segments_list]

    print("--------------")

    # 提供給 GPT 的輸入
    gpt_input = ""
    for i in range(len(text_list)):
        gpt_input += text_list[i] + "\n"


    gpt_input += "\n\n請你依據内容幫我分段，段落長度不限，希望每個影片大概4到5分鐘，然後每段的開頭都要注記那一段的主題是什麽。你不能自己增加内容或更改標點符號，只能依據我給你的文本。"


    prompt = f"""你是一位負責把文章分段的機器人，必須要將使用者給的文本依內容分段，不限段落長短。絕對不能忽略、刪除、更改、增加任何句子、標點符號、文字、空格、換行，必須完整保留整個文本不變。每句話中間空一格。每段請以 '摘要\n=======\n分段內容\n---------\n' ，以下是範例
    摘要
    =======
    部落防災
    ---------
    要不然來不及 這個就是龍魚什麼 的格式輸出：\n\n{gpt_input}"""


    # 調用 OpenAI API
    load_dotenv()  # 從 .env 文件加載 API 密鑰
    API_KEY = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=API_KEY)

    completion = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.5,
        max_tokens=4000,
        messages=[
            {
                "role": "system",
                "content": "所有回答必需遵循以下格式且不能改原文，不能省略任何字：\n摘要\n=======\n{摘要內容}\n---------\n{段落内容}\n\n",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ]           
    )

    # 分段完成結果存到 gpt_output
    gpt_output = completion.choices[0].message.content  # 保存分段結果

    # check
    print(gpt_output)  # GPT 分段結果
    print("GPT 分段完成")

    gpt_path = "gpt_output.txt"
    try:
        # 保存 GPT 輸出結果
        with open(output_folder + "/words/gpt_output.txt", "w", encoding="utf-8") as file:
            file.write(gpt_output)
    except Exception as e:
        print(f"保存文件時發生錯誤: {e}")




    # 存儲摘要和內容的列表
    titles = []
    contents = []

    try:
        # 根據 [段落摘要] 和 [段落內容] 分割結果
        matches = re.findall(
            r"摘要\s*=======\s*(.*?)\s*---------\s*(.*?)(?=摘要\s*=======|\Z)", gpt_output, re.DOTALL
        )

        if not matches:
            raise ValueError("No matches found in GPT output. Please check the format of the input")

        # 保存到 titles 和 contents 列表中
        for match in matches:
            titles.append(match[0].strip())  # 摘要部分
            contents.append(match[1].strip())  # 內容部分

        print("匹配內容儲存完成\n")
        print(f"titles: {titles}")
        print(f"contents: {contents}")

### 保存每段文字的開始與結束時間戳 ###
        # 依據該列表進行剪輯        
        paragraph_timestamps = []
        tmp = -1

        # 按照分段內容，在 segments_list 中找到開始與結束的時間戳
        for paragraph in contents:
            print(f"paragraph:::\n{paragraph}")
            start_timestamp = None
            end_timestamp = None
            current_text = ""  # 儲存當前段落的文本

            start_idx = tmp if tmp != -1 else 0

            for index in range(start_idx, len(segments_list)):
                segment = segments_list[index]
                print(f">>> {segment} in segments_list")
                _, end_time, segment_text = segment


                # 在段落中確認是否包含 segment_text
                if segment_text in paragraph:

                    if start_timestamp is None:
                        # 將段落的開始時間戳設定為第一次匹配的位置
                        start_timestamp = segment[0]

                    # 將段落的結束時間戳設定為最後匹配的位置
                    current_text += segment_text + "\n"
                    end_timestamp = end_time
                    print(f"{start_timestamp} ~ {end_timestamp} for this turn")
                    print(f"current_txt::{current_text}")  # 檢查


                    # 如果目前的文本與段落相同，則break
                    if paragraph.startswith(current_text):
                        print(f"current_txt::{current_text}")  # 檢查
                        print("段落結束")
                        break
                else:
                    tmp = index
                    if start_timestamp and end_timestamp:
                        paragraph_timestamps.append((start_timestamp, end_timestamp))
                        print(f"{start_timestamp} ~ {end_timestamp} appended")
                        print("========== 段落結束 ==========\n")
                    break

    except ValueError as ve:
        print(f"ValueError: {ve}")
    except re.error as re_err:
        print(f"RegexError: {re_err}")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")

    
### ffmpeg ###

    db = get_cursor()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        clip_number = 0

        for i, (start, end) in enumerate(paragraph_timestamps):
            print(f"{i+1} 段落: {start} ~ {end}")

            output_file = os.path.join(output_folder_edited, f"{titles[i]}.mp4")

            try:
                subprocess.run([
                    "ffmpeg",
                    "-i", input_file,
                    "-ss", start.split(',')[0],
                    "-to", end.split(',')[0],
                    "-c:v", "copy",
                    "-c:a", "copy",
                    output_file
                ], check=True)
                print(f"成功創建: {output_file}")

                ### 儲存到DB ###
                clip_number += 1
                clip_path = f"upload/{file_id}/edited"
                clip_name = titles[i]
                format = ".mp4"  # 剪輯格式
                title = titles[i]  # 摘要
                content = contents[i]  # 內容

                query = """
                    INSERT INTO edited (source_id, clip_path, clip_name, format, clip_number, start, end, title, contents)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (file_id, clip_path, clip_name, format, clip_number, start.split(',')[0], end.split(',')[0], title, content))
                db.commit()

                # 更新原始文件的status為 1
                update_query = "UPDATE uploaded SET status = %s WHERE file_id = %s"
                cursor.execute(update_query, (1, file_id))
                db.commit()

                print("剪輯保存到數據庫並更新原始影片狀態成功")


            except subprocess.CalledProcessError as e:
                db.rollback()  # 插入失敗時回滾
                print(f"Error during FFmpeg execution: {e}")



    except Exception as e:
        db.rollback()  # 插入失敗時回滾
        print(f"數據庫操作時發生錯誤: {e}")

    finally:
        cursor.close()

    return tuple
