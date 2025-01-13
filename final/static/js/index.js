window.onload = fetchVideos;

function fetchVideos() {
    // 從 Flask 的 /index 端點獲取 JSON 數據
    fetch("/index")
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 錯誤！狀態碼: ${response.status}`);
            }
            return response.json();
        }).then(data => {
            console.log(data); // 用於調試
            const videoList = document.getElementById('video-list');
            videoList.innerHTML = '';

            if (Array.isArray(data) && data.length > 0) {
                data.forEach(video => {
                    console.log(video.file_path);
                    console.log(video.file_name);
                    
                    // 創建影片容器元素
                    const videoElement = document.createElement("div");
                    videoElement.classList.add("video-item");
                    videoElement.innerHTML = `
                        <button class="video-button" onclick="openModal('${video.file_path}/${video.file_name}', '${video.file_name}')">
                            <video controls id="video-${video.file_name}">
                                <source src="${video.file_path}/${video.file_name}" type="video/mp4">
                                    您的瀏覽器不支持 video 標籤。
                            </video>
                            <div class="video-details">
                                <div class="video_file_name">${video.file_name}</div>
                                <div class="video_duration">
                                    <span id="duration-${video.file_name}">(加載中...)</span>
                                </div>
                                <button class="edit-button" onclick="sendVideoInfo('${video.file_path}', '${video.file_name}')">編輯</button>
                                <button class="delete-button" onclick="deleteVideo('${video.file_name}')">刪除</button>
                            </div>
                        </button>
                    `;
                    
                    // 設定點擊事件處理程序以傳送影片資訊
                    videoList.appendChild(videoElement);

                    // 在元數據加載完成後獲取影片時長
                    const videoElementInstance = document.getElementById(`video-${video.file_name}`);
                    videoElementInstance.addEventListener("loadedmetadata", () => {
                        const duration = formatDuration(videoElementInstance.duration); // 格式化時長
                        document.getElementById(`duration-${video.file_name}`).textContent = duration;
                    });
                });
            } else {
                videoList.innerHTML = "<li>未找到最近的影片。</li>";
            }
        })
        .catch(error => {
            console.error("獲取影片數據時出錯:", error);
            videoList.innerHTML = "<li>加載影片失敗。</li>";
        });
}

// 將時長格式化為 MM:SS
function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}



function sendVideoInfo(url, filename) {
    console.log("sendVideoInfo 被調用，參數為:", url, filename); // 檢查
    // 使用 POST 請求傳送影片資訊
    fetch('/cutVideo', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url, filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.redirect_url) {
            // 跳轉到服務器提供的重定向 URL
            window.location.href = data.redirect_url;
        } else {
            console.error("未提供重定向 URL。");
        }
    })
    .catch(error => {
        console.error('傳送影片資訊時出錯:', error);
    });

    // 在控制台輸出 URL 和文件名
    console.log('影片 URL:', url);
    console.log('影片文件名:', filename);
}



// 上傳
document.getElementById("uploadButton").addEventListener("click", function () {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];

    if (file) {
        const formData = new FormData();
        formData.append("file", file);

        fetch("/upload", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log("成功:", data);
        })
        .catch((error) => {
            console.error("錯誤:", error);
        });
    } else {
        alert("請先選擇一個文件。");
    }
});


// 刪除按鈕
videoList.addEventListener('click', (event) => {
    if (event.target.classList.contains('delete-button')) {
        const fileName = event.target.getAttribute('data-filename');
        console.log(`正在刪除影片: ${fileName}`);
        deleteVideo(fileName);
    } else if (event.target.closest('.video-button')) {
        const videoButton = event.target.closest('.video-button');
        const filePath = videoButton.getAttribute('data-file-path');
        const fileName = videoButton.getAttribute('data-file-name');
        sendVideoInfo(filePath, fileName);
    }
});


function deleteVideo(filename) {
    console.log("<deleteVideo>",filename)
    event.stopPropagation();  // 防止觸發影片播放

    const source = window.location.pathname;

    fetch("/delete", {
        method: "POST", // 使用 POST 而非 DELETE，Flask 中 DELETE 處理也可以使用 POST 請求
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            file_name: filename,
            source: source
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("影片刪除成功");
            //location.reload(); // 刪除後重新加載頁面
            window.location.href = data.redirect_url;
        } else {
            alert(`刪除影片時出錯: ${data.error}`);
        }
    })
    .catch(error => {
        console.error("錯誤:", error);
        alert("刪除影片時發生錯誤。");
    });
}


// 模態彈出視窗
function openModal(videoSrc, videoName) {
    const modal = document.getElementById("video-modal");
    const modalVideoSource = document.getElementById("modal-video-source");
    const modalVideoDetails = document.getElementById("modal-video-details");

    modalVideoSource.src = videoSrc;
    modalVideoDetails.textContent = `正在播放: ${videoName}`;

    modal.style.display = "block";
    modalVideoSource.parentElement.load(); // 在模態中重新加載影片
}

// 關閉模態彈出視窗
function closeModal() {
    const modal = document.getElementById("video-modal");
    const modalVideoSource = document.getElementById("modal-video-source");

    modal.style.display = "none";
    modalVideoSource.src = ""; // 清除影片來源以停止播放
}


// 點擊模態外部時關閉
window.onclick = function (event) {
    const modal = document.getElementById("video-modal");
    if (event.target === modal) {
        closeModal();
    }
};
