// 選擇的影片下載函數
function download() {
    // 選擇所有被勾選的複選框
    const checkboxes = document.querySelectorAll('.video-checkbox:checked');
    if (checkboxes.length === 0) {
        alert("請至少選擇一個影片進行下載。");
        return;
    }

    // 使用每個複選框的 URL 生成下載連結並觸發點擊
    checkboxes.forEach(checkbox => {
        const videoUrl = checkbox.value;
        const a = document.createElement('a');
        a.href = videoUrl;
        a.download = videoUrl.split('/').pop(); // 設定檔案名稱
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });
}



// 模態彈出視窗

// 開啟模態
function showModal(videoUrl, filename) {
    // 調用 Flask API
    fetch(`/get_clip_metadata?filename=${encodeURIComponent(filename)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 錯誤！狀態碼: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.title && data.contents) {
                // 將影片路徑與元數據插入模態中
                const modalVideo = document.getElementById("modal-video");
                const modalVideoSource = document.getElementById("modal-video-source");
                const modalFilename = document.getElementById("modal-filename");

                // 更新影片來源和文字
                modalVideoSource.src = videoUrl;
                modalFilename.innerHTML = `<strong>標題:</strong> ${data.title}<br><strong>內容:</strong> ${data.contents}`;

                // 重新加載影片元素
                modalVideo.load();

                // 顯示模態
                const modal = document.getElementById("modal");
                modal.style.display = "block";
            } else {
                console.error("未找到檔案的元數據:", filename);
            }
        })
        .catch(error => {
            console.error("獲取元數據時出錯:", error);
        });
}

function closeModal() {
    // 關閉模態
    const modal = document.getElementById("modal");
    modal.style.display = "none";

    // 停止影片
    const modalVideo = document.getElementById("modal-video");
    modalVideo.pause();
}



// 點擊模態外部時關閉
window.onclick = function (event) {
    const modal = document.getElementById("modal");
    if (event.target === modal) {
        closeModal();
    }
};



function backtohome(){
    window.location.href = '/';
}


function toggleBorder(checkbox) {
    const videoItem = checkbox.closest('.video-item'); // 找到父元素 video-item
    if (checkbox.checked) {
        videoItem.style.border = '3px solid #007bff'; // 勾選時邊框為藍色
    } else {
        videoItem.style.border = '2px solid transparent'; // 取消勾選時恢復初始狀態
    }
}



// 點擊複選框時防止事件冒泡
function stopPropagation(event) {
    console.log("複選框被點擊，事件冒泡已停止。");
    event.stopPropagation(); // 防止事件冒泡到父元素
    event.preventDefault();  // 阻止默認行為（如有需要）
}
