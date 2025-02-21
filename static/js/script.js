document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('scratchCanvas');
    const ctx = canvas.getContext('2d');
    const prizeDiv = document.getElementById('prize');

    // 初始化涂层
    ctx.fillStyle = '#c0c0c0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 鼠标事件
    canvas.addEventListener('mousedown', startScratch);
    canvas.addEventListener('mousemove', scratch);
    canvas.addEventListener('mouseup', endScratch);
    canvas.addEventListener('touchstart', startScratch);
    canvas.addEventListener('touchmove', scratch);
    canvas.addEventListener('touchend', endScratch);

    let isScratching = false;

    function startScratch(e) {
        isScratching = true;
        scratch(e);
    }

    function scratch(e) {
        if (!isScratching) return;
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        ctx.globalCompositeOperation = 'destination-out';
        ctx.beginPath();
        ctx.arc(x, y, 20, 0, Math.PI * 2);
        ctx.fill();
        checkCompletion();
    }

    function endScratch() {
        isScratching = false;
    }

    function checkCompletion() {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const pixelCount = imageData.data.length / 4;
        let transparentPixels = 0;

        for (let i = 0; i < pixelCount; i++) {
            if (imageData.data[i * 4 + 3] === 0) {
                transparentPixels++;
            }
        }

        if (transparentPixels > pixelCount * 0.8) {
            revealPrize();
        }
    }

    function revealPrize() {
        const prizes = ['一等奖', '二等奖', '三等奖', '谢谢参与'];
        const probabilities = [0.1, 0.2, 0.3, 0.4];
        let random = Math.random();
        let cumulativeProbability = 0;

        for (let i = 0; i < probabilities.length; i++) {
            cumulativeProbability += probabilities[i];
            if (random < cumulativeProbability) {
                prizeDiv.textContent = prizes[i];
                prizeDiv.style.display = 'block';
                break;
            }
        }
    }
});